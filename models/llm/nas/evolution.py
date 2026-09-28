from __future__ import annotations

import copy
import json
import logging
import math
import random
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import torch

from models.llm.nas.search import NASSearchSpace, ArchitectureGenome

logger = logging.getLogger(__name__)


@dataclass
class SearchRecord:
    generation: int
    genome: ArchitectureGenome
    score: float
    params: int
    elapsed_seconds: float
    rank: int
    status: str = "completed"
    error: Optional[str] = None


class NASEvolution:
    def __init__(
        self,
        search_space: NASSearchSpace,
        population_size: int = 16,
        elite_size: int = 4,
        tournament_size: int = 3,
        mutation_rate: float = 0.3,
        crossover_rate: float = 0.6,
        max_generations: int = 20,
        seed: int = 42,
    ) -> None:
        self.search_space = search_space
        self.population_size = int(population_size)
        self.elite_size = int(elite_size)
        self.tournament_size = int(tournament_size)
        self.mutation_rate = float(mutation_rate)
        self.crossover_rate = float(crossover_rate)
        self.max_generations = int(max_generations)
        self.seed = int(seed)

        self.rng = random.Random(seed)
        self.generation: int = 0
        self.population: List[ArchitectureGenome] = []
        self.history: List[Dict[str, Any]] = []
        self.best_genome: Optional[ArchitectureGenome] = None
        self.best_score: float = float("-inf")
        self.stagnation_count: int = 0
        self.stagnation_threshold: int = max(5, self.max_generations // 4)
        self.best_score_at_stagnation: float = float("-inf")

    def initialize_population(self, strategy: str = "random") -> List[ArchitectureGenome]:
        seeds = self.search_space.get_seed_genomes()
        population: List[ArchitectureGenome] = []
        for seed_genome in seeds:
            g = seed_genome.copy()
            g.parent_ids = []
            g.mutation = None
            g.metadata = {}
            population.append(g)
        for _ in range(max(0, self.population_size - len(population))):
            population.append(self.search_space.sample_genome(strategy))
        self.population = population[: self.population_size]
        self.generation = 0
        return self.population

    def _tournament_select(self) -> ArchitectureGenome:
        candidates = self.rng.sample(self.population, min(self.tournament_size, len(self.population)))
        return max(candidates, key=lambda g: g.fitness())

    def _rank_select(self, rank: int) -> float:
        n = len(self.population)
        if n == 0:
            return 0.0
        return 2.0 * (n - rank) / (n * (n - 1)) if n > 1 else 1.0

    def selection_pressure(self) -> float:
        n = len(self.population)
        if n == 0:
            return 0.0
        fitnesses = sorted([g.fitness() for g in self.population], reverse=True)
        if n == 1:
            return fitnesses[0]
        return fitnesses[0] - fitnesses[-1]

    def _linear_rank_selection(self) -> ArchitectureGenome:
        ranked = sorted(self.population, key=lambda g: g.fitness(), reverse=True)
        probabilities = [self._rank_select(i) for i in range(len(ranked))]
        total = sum(probabilities)
        if total == 0:
            return self.rng.choice(self.population)
        pick = self.rng.uniform(0, total)
        cumulative = 0.0
        for genome, prob in zip(ranked, probabilities):
            cumulative += prob
            if pick <= cumulative:
                return genome
        return ranked[-1]

    def elitism(self, candidates: List[ArchitectureGenome]) -> List[ArchitectureGenome]:
        if not candidates:
            return []
        ranked = sorted(candidates, key=lambda g: g.fitness(), reverse=True)
        elite = [g.copy() for g in ranked[: self.elite_size]]
        return elite

    def evolve_generation(
        self, evaluator: Any, device: str = "cpu"
    ) -> List[Dict[str, Any]]:
        if self.generation == 0 and not self.population:
            self.initialize_population()
        if not self.population:
            raise RuntimeError("Population is empty, call initialize_population first.")

        gen_start = time.time()
        records: List[Dict[str, Any]] = []

        for genome in self.population:
            score, param_count, elapsed = self._evaluate(genome, evaluator, device)
            genome.metadata["fitness"] = score
            genome.metadata["params"] = param_count
            genome.metadata["elapsed"] = elapsed
            genome.metadata["genome"] = genome.genome_id
            genome.metadata["generation"] = self.generation

            record = SearchRecord(
                generation=self.generation,
                genome=genome,
                score=score,
                params=param_count,
                elapsed_seconds=elapsed,
                rank=0,
                status="completed",
            )
            records.append({
                "generation": self.generation,
                "genome_id": genome.genome_id,
                "score": score,
                "params": param_count,
                "elapsed": elapsed,
                "genome": genome,
                "record": record,
            })

        records.sort(key=lambda r: r["score"], reverse=True)
        for rank, rec in enumerate(records):
            rec["record"].rank = rank
            rec["record"].score = rec["score"]

        for rec in records:
            if rec["score"] > self.best_score:
                self.best_score = rec["score"]
                self.best_genome = rec["genome"]
                self.best_genome.metadata["fitness"] = rec["score"]
                self.stagnation_count = 0
                self.best_score_at_stagnation = self.best_score

        current_elite = self.elitism([r["genome"] for r in records])
        next_pop: List[ArchitectureGenome] = [g.copy() for g in current_elite]

        while len(next_pop) < self.population_size:
            if self.rng.random() < self.crossover_rate and len(self.population) >= 2:
                parent_a = self._tournament_select()
                parent_b = self._tournament_select()
                child = self.search_space.crossover(parent_a, parent_b)
            else:
                parent = self._tournament_select()
                child = self.search_space.mutate(parent)
                child.mutation = child.mutation or "mutation"
                child.parent_ids = [parent.genome_id]
                child.generation = self.generation + 1

            if self.rng.random() < self.mutation_rate:
                child = self.search_space.mutate(child)
                if child.mutation == "identity":
                    child.mutation = "mutation"
                child.generation = self.generation + 1

            child.metadata = {}
            next_pop.append(child)

        self.population = next_pop[: self.population_size]
        self.generation += 1
        self.history.append({
            "generation": self.generation - 1,
            "records": records,
            "elite": current_elite,
            "best_score": self.best_score,
            "mean_score": sum(r["score"] for r in records) / len(records) if records else 0.0,
            "elapsed_seconds": time.time() - gen_start,
        })
        return records

    def _evaluate(
        self, genome: ArchitectureGenome, evaluator: Any, device: str
    ) -> tuple[float, int, float]:
        try:
            return evaluator.evaluate(genome, device=device)
        except Exception as exc:
            logger.exception("Failed to evaluate genome %s", genome.genome_id)
            return float("-inf"), 0, 0.0

    def check_stopping_criterion(self) -> tuple[bool, str]:
        if self.generation >= self.max_generations:
            return True, f"max_generations={self.max_generations} reached"
        if self.best_score_at_stagnation != float("-inf"):
            if self.best_score - self.best_score_at_stagnation < 1e-4:
                self.stagnation_count += 1
            else:
                self.stagnation_count = 0
                self.best_score_at_stagnation = self.best_score
        if self.stagnation_count >= self.stagnation_threshold:
            return True, f"stagnated for {self.stagnation_count} generations"
        if not self.population:
            return True, "population is empty"
        return False, ""

    def run_search(
        self, evaluator: Any, device: str = "cpu"
    ) -> List[SearchRecord]:
        if not self.population:
            self.initialize_population()
        self.best_score = float("-inf")
        self.best_genome = None
        self.stagnation_count = 0
        self.best_score_at_stagnation = float("-inf")
        self.history = []
        self.generation = 0

        while True:
            records = self.evolve_generation(evaluator, device)
            should_stop, reason = self.check_stopping_criterion()
            if should_stop:
                break

        return self.get_results()

    def get_results(self) -> List[SearchRecord]:
        results: List[SearchRecord] = []
        for hist in self.history:
            for rec in hist.get("records", []):
                results.append(SearchRecord(
                    generation=hist["generation"],
                    genome=rec["genome"],
                    score=rec["score"],
                    params=rec["params"],
                    elapsed_seconds=rec["elapsed"],
                    rank=rec["record"].rank,
                    status=rec["record"].status,
                    error=rec["record"].error,
                ))
        return sorted(results, key=lambda r: r.score, reverse=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "population_size": self.population_size,
            "elite_size": self.elite_size,
            "tournament_size": self.tournament_size,
            "mutation_rate": self.mutation_rate,
            "crossover_rate": self.crossover_rate,
            "max_generations": self.max_generations,
            "seed": self.seed,
            "current_generation": self.generation,
            "best_score": self.best_score,
            "population_count": len(self.population),
            "history_length": len(self.history),
            "stagnation_count": self.stagnation_count,
        }

    def generate_report(self) -> str:
        lines: List[str] = []
        lines.append("# NAS Search Report")
        lines.append("")
        lines.append(f"- **Generations**: {self.generation}")
        lines.append(f"- **Population**: {self.population_size}")
        lines.append(f"- **Elite**: {self.elite_size}")
        lines.append(f"- **Best score**: {self.best_score:.6f}")
        lines.append(f"- **Stagnation**: {self.stagnation_count} generations")
        lines.append(f"- **Seed**: {self.seed}")
        lines.append("")

        if self.history:
            lines.append("## Per-Generation Summary")
            for hist in self.history:
                lines.append(f"\n- Gen {hist['generation']}: best={hist['best_score']:.4f}, mean={hist['mean_score']:.4f}")

        if self.best_genome:
            lines.append("\n## Best Genome")
            for k, v in self.best_genome.as_config().items():
                lines.append(f"- `{k}`: {v}")

        return "\n".join(lines)
