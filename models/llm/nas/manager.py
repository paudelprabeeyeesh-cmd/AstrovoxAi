from __future__ import annotations

import copy
import json
import logging
import math
import time
from dataclasses import asdict, dataclass, field, fields
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from models.llm.nas.evolution import NASEvolution, SearchRecord
from models.llm.nas.evaluator import ArchitectureEvaluator, EvalResult
from models.llm.nas.search import ArchitectureGenome, NASSearchSpace

logger = logging.getLogger(__name__)


@dataclass
class SearchCheckpoint:
    generation: int
    population: List[Any]
    best_genome: Optional[Any]
    best_score: float
    history: List[Dict[str, Any]]
    stagnation_count: int
    elapsed_seconds: float
    device: str
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        # The resumable state has to be written in full. Recording only
        # counts makes the checkpoint lossy, so restoring from it would
        # either fail outright or silently restart the search.
        return {
            "generation": self.generation,
            "best_score": self.best_score,
            "elapsed_seconds": self.elapsed_seconds,
            "stagnation_count": self.stagnation_count,
            "device": self.device,
            "timestamp": self.timestamp,
            "config": self.config,
            "population": [_record_to_dict(entry) for entry in self.population],
            "best_genome": _genome_to_dict(self.best_genome),
            "history": self.history,
        }


def _genome_to_dict(genome: Any) -> Optional[Dict[str, Any]]:
    """Return a JSON-serializable copy of a genome's declared fields."""
    if genome is None:
        return None
    if isinstance(genome, dict):
        return dict(genome)
    return asdict(genome)


def _genome_from_dict(data: Optional[Dict[str, Any]]) -> Optional[ArchitectureGenome]:
    """Rebuild an :class:`ArchitectureGenome` from its stored fields.

    Only known fields are passed through, so a checkpoint written under a
    different schema still restores instead of raising ``TypeError``.
    """
    if not data:
        return None
    known = {f.name for f in fields(ArchitectureGenome)}
    return ArchitectureGenome(**{k: v for k, v in data.items() if k in known})


def _record_to_dict(record: Any) -> Dict[str, Any]:
    """Serialize a population entry, which may be a record or a bare genome."""
    if isinstance(record, SearchRecord):
        data = asdict(record)
        data["genome"] = _genome_to_dict(record.genome)
        return data
    return {"genome": _genome_to_dict(record)}


def _record_from_dict(data: Any) -> Any:
    """Rebuild a population entry written by :func:`_record_to_dict`.

    Entries are written either as a full record (when the population holds
    ``SearchRecord`` objects) or as a bare genome, so the shape of the stored
    entry decides what is rebuilt. Requiring the record's own fields keeps the
    two cases from being confused with one another.
    """
    if not data:
        return None
    if "genome" not in data:
        return _genome_from_dict(data)
    genome = _genome_from_dict(data["genome"])
    record_fields = {f.name for f in fields(SearchRecord) if f.name != "genome"}
    if not record_fields.issubset(data.keys()):
        # Only a genome was stored; restore it as one.
        return genome
    payload = {k: data[k] for k in record_fields}
    return SearchRecord(genome=genome, **payload)


class NASManager:
    def __init__(
        self,
        search_space: NASSearchSpace,
        evaluator: ArchitectureEvaluator,
        output_dir: str | Path = "nas_output",
        population_size: int = 16,
        elite_size: int = 4,
        tournament_size: int = 3,
        mutation_rate: float = 0.3,
        crossover_rate: float = 0.6,
        max_generations: int = 20,
        max_elapsed_seconds: Optional[float] = None,
        early_stopping_patience: int = 8,
        seed: int = 42,
        checkpoint_dir: Optional[str | Path] = None,
        device: str = "cpu",
    ) -> None:
        self.search_space = search_space
        self.evaluator = evaluator
        self.output_dir = Path(output_dir)
        self.population_size = int(population_size)
        self.elite_size = int(elite_size)
        self.tournament_size = int(tournament_size)
        self.mutation_rate = float(mutation_rate)
        self.crossover_rate = float(crossover_rate)
        self.max_generations = int(max_generations)
        self.max_elapsed_seconds = max_elapsed_seconds
        self.early_stopping_patience = int(early_stopping_patience)
        self.seed = int(seed)
        self.device = device

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_dir = Path(checkpoint_dir) if checkpoint_dir else self.output_dir / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self.evolution = NASEvolution(
            search_space=search_space,
            population_size=population_size,
            elite_size=elite_size,
            tournament_size=tournament_size,
            mutation_rate=mutation_rate,
            crossover_rate=crossover_rate,
            max_generations=max_generations,
            seed=seed,
        )
        self.start_time: Optional[float] = None
        self.best_results: List[SearchRecord] = []
        self.steps_without_improvement: int = 0

    def search(self) -> Dict[str, Any]:
        self.start_time = time.time()
        last_checkpoint_gen: int = 0
        best_score_so_far: float = float("-inf")

        while self.evolution.generation < self.max_generations:
            records = self.evolution.evolve_generation(self.evaluator, device=self.device)
            if not records:
                break

            gen_best = max(records, key=lambda r: r["score"])
            if gen_best["score"] > best_score_so_far:
                best_score_so_far = gen_best["score"]
                self.steps_without_improvement = 0
            else:
                self.steps_without_improvement += 1

            should_stop, reason = self._early_stop(self.evolution.generation)
            if should_stop:
                logger.info("Early stopping at generation %d: %s", self.evolution.generation, reason)
                break

            if self._should_checkpoint(self.evolution.generation, last_checkpoint_gen):
                self._save_checkpoint(self.evolution.generation)
                last_checkpoint_gen = self.evolution.generation

            logger.info(
                "Generation %d/%d: best_score=%.4f, gen_mean=%.4f, patience=%d/%d",
                self.evolution.generation,
                self.max_generations,
                best_score_so_far,
                sum(r["score"] for r in records) / len(records),
                self.steps_without_improvement,
                self.early_stopping_patience,
            )

        self.best_results = self._rank_results()
        self._save_final_results()
        return self._build_summary()

    def _should_checkpoint(self, generation: int, last: int) -> bool:
        if generation == 0:
            return True
        if generation % 4 == 0:
            return True
        if generation - last >= 4:
            return True
        return False

    def _early_stop(self, generation: int) -> Tuple[bool, str]:
        if self.early_stopping_patience > 0:
            if self.steps_without_improvement >= self.early_stopping_patience:
                return True, f"no improvement for {self.steps_without_improvement} generations"
        elapsed = time.time() - self.start_time if self.start_time else 0.0
        if self.max_elapsed_seconds is not None and elapsed > self.max_elapsed_seconds:
            return True, f"time budget of {self.max_elapsed_seconds}s exceeded (elapsed={elapsed:.1f}s)"
        return False, ""

    def _save_checkpoint(self, generation: int) -> None:
        if not self.checkpoint_dir.exists():
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        ckpt = SearchCheckpoint(
            generation=generation,
            population=[self._genome_to_dict(g) for g in self.evolution.population],
            best_genome=self._genome_to_dict(self.evolution.best_genome) if self.evolution.best_genome else None,
            best_score=self.evolution.best_score,
            history=copy.deepcopy(self.evolution.history),
            stagnation_count=self.evolution.stagnation_count,
            elapsed_seconds=time.time() - self.start_time if self.start_time else 0.0,
            device=self.device,
            config=self.get_config(),
        )
        path = self.checkpoint_dir / f"checkpoint_gen{generation:04d}.json"
        path.write_text(json.dumps(ckpt.to_dict(), indent=2, default=str))
        logger.info("Saved checkpoint to %s", path)

    def _genome_to_dict(self, genome: Optional[Any]) -> Optional[Dict[str, Any]]:
        if genome is None:
            return None
        d = copy.deepcopy(genome.as_config())
        d.update({
            "genome_id": genome.genome_id,
            "parent_ids": genome.parent_ids,
            "mutation": genome.mutation,
            "generation": genome.generation,
            "metadata": genome.metadata,
        })
        return d

    def _save_final_results(self) -> None:
        results_path = self.output_dir / "best_architectures.json"
        top = [r for r in self.best_results[:20] if r.score > float("-inf")]
        results = [
            {
                "rank": i + 1,
                "genome_id": r.genome.genome_id,
                "architecture_family": r.genome.architecture_family,
                "score": r.score,
                "params": r.params,
                "elapsed": r.elapsed_seconds,
                "genome": r.genome.as_config(),
            }
            for i, r in enumerate(top)
        ]
        results_path.write_text(json.dumps(results, indent=2, default=str))
        summary_path = self.output_dir / "summary.md"
        summary_path.write_text(self.evolution.generate_report())

    def _build_summary(self) -> Dict[str, Any]:
        elapsed = time.time() - self.start_time if self.start_time else 0.0
        return {
            "best_score": self.evolution.best_score,
            "best_genome": self.evolution.best_genome.as_config() if self.evolution.best_genome else None,
            "best_genome_id": self.evolution.best_genome.genome_id if self.evolution.best_genome else None,
            "generations": self.evolution.generation,
            "population_size": self.population_size,
            "best_results": self.best_results[:10],
            "elapsed_seconds": elapsed,
            "early_stop_steps": self.steps_without_improvement,
            "config": self.get_config(),
        }

    def _rank_results(self) -> List[SearchRecord]:
        all_records = self.evolution.get_results()
        seen: Dict[str, SearchRecord] = {}
        for r in all_records:
            gid = r.genome.genome_id
            if gid not in seen or r.score > seen[gid].score:
                seen[gid] = r
        ranked = sorted(seen.values(), key=lambda r: r.score, reverse=True)
        for i, r in enumerate(ranked):
            r.rank = i + 1
        return ranked

    def load_checkpoint(self, checkpoint_path: str | Path) -> SearchCheckpoint:
        path = Path(checkpoint_path)
        if not path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {path}")
        data = json.loads(path.read_text())
        ckpt = SearchCheckpoint(
            generation=data["generation"],
            population=data.get("population", []),
            best_genome=data.get("best_genome"),
            best_score=data["best_score"],
            history=data.get("history", []),
            stagnation_count=data.get("stagnation_count", 0),
            elapsed_seconds=data.get("elapsed_seconds", 0.0),
            device=data.get("device", self.device),
            timestamp=data.get("timestamp", datetime.now(UTC).isoformat()),
            config=data.get("config", {}),
        )
        return ckpt

    def restore_from_checkpoint(self, checkpoint_path: str | Path) -> None:
        ckpt = self.load_checkpoint(checkpoint_path)
        self.evolution.generation = ckpt.generation
        self.evolution.best_score = ckpt.best_score
        self.evolution.best_genome = _genome_from_dict(ckpt.best_genome)
        self.evolution.history = ckpt.history
        self.evolution.stagnation_count = ckpt.stagnation_count
        self.evolution.best_score_at_stagnation = ckpt.best_score
        # Restoring the population is what makes a resume continue the search
        # rather than silently restart it from a fresh random sample.
        if ckpt.population:
            self.evolution.population = [
                _record_from_dict(entry) for entry in ckpt.population
            ]
        self.steps_without_improvement = 0
        self.start_time = time.time() - ckpt.elapsed_seconds
        logger.info("Restored from checkpoint at generation %d", ckpt.generation)

    def get_config(self) -> Dict[str, Any]:
        return {
            "population_size": self.population_size,
            "elite_size": self.elite_size,
            "tournament_size": self.tournament_size,
            "mutation_rate": self.mutation_rate,
            "crossover_rate": self.crossover_rate,
            "max_generations": self.max_generations,
            "max_elapsed_seconds": self.max_elapsed_seconds,
            "early_stopping_patience": self.early_stopping_patience,
            "seed": self.seed,
            "device": self.device,
            "output_dir": str(self.output_dir),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config": self.get_config(),
            "best_score": self.evolution.best_score,
            "generations": self.evolution.generation,
            "best_results_count": len(self.best_results),
        }
