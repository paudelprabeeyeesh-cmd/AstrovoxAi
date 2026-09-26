import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ArchitectureCandidate:
    layers: list[dict[str, Any]]
    parameters: int = 0
    score: float = 0.0


class EvolutionaryArchitectureOptimizer:
    def __init__(self, population_size: int = 10):
        self.population_size = population_size
        self.population: list[ArchitectureCandidate] = []
        self.generation: int = 0

    def initialize(self) -> list[ArchitectureCandidate]:
        self.population = [
            ArchitectureCandidate(layers=[{"type": "linear", "size": 128}], parameters=128, score=0.1)
            for _ in range(self.population_size)
        ]
        return self.population

    def select(self, k: int = 3) -> list[ArchitectureCandidate]:
        return sorted(self.population, key=lambda x: x.score, reverse=True)[:k]

    def crossover(self, parent_a: ArchitectureCandidate, parent_b: ArchitectureCandidate) -> ArchitectureCandidate:
        child = ArchitectureCandidate(
            layers=parent_a.layers[: len(parent_a.layers) // 2] + parent_b.layers[len(parent_b.layers) // 2 :],
            parameters=parent_a.parameters + parent_b.parameters,
        )
        return child

    def mutate(self, candidate: ArchitectureCandidate) -> ArchitectureCandidate:
        candidate.layers.append({"type": "mutation", "size": 64})
        candidate.parameters += 64
        return candidate

    def evolve(self, fitness_scores: list[float]) -> list[ArchitectureCandidate]:
        if not self.population:
            self.initialize()
        for i, score in enumerate(fitness_scores):
            if i < len(self.population):
                self.population[i].score = score
        next_gen: list[ArchitectureCandidate] = []
        for _ in range(self.population_size):
            parents = self.select(2)
            child = self.crossover(parents[0], parents[1])
            child = self.mutate(child)
            next_gen.append(child)
        self.population = next_gen
        self.generation += 1
        return self.population
