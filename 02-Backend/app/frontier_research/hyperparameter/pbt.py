"""Population-based training (PBT) and hyperparameter optimization utilities."""

from __future__ import annotations

import logging
import random
import math
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class HyperparameterSpec:
    name: str
    low: float
    high: float
    scale: str = "linear"
    dtype: str = "float"


@dataclass
class Individual:
    hyperparameters: dict[str, Any]
    fitness: float = -math.inf
    step: int = 0


class PopulationBasedTrainer:
    def __init__(
        self,
        hyperparameters: list[HyperparameterSpec],
        population_size: int = 8,
        exploit_factor: float = 0.2,
        explore_factor: float = 0.2,
    ):
        self.hyperparameters = hyperparameters
        self.population_size = population_size
        self.exploit_factor = exploit_factor
        self.explore_factor = explore_factor
        self.population: list[Individual] = []
        self.generation = 0

    def _sample_hyperparameters(self) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for spec in self.hyperparameters:
            value = random.random() * (spec.high - spec.low) + spec.low
            if spec.scale == "log":
                value = math.exp(math.log(spec.low) + random.random() * (math.log(spec.high) - math.log(spec.low)))
            if spec.dtype == "int":
                value = int(round(value))
            values[spec.name] = value
        return values

    def initialize(self) -> list[Individual]:
        self.population = [Individual(hyperparameters=self._sample_hyperparameters()) for _ in range(self.population_size)]
        return self.population

    def step(self, evaluate_fn: Callable[[dict[str, Any]], float]) -> dict[str, Any]:
        if not self.population:
            self.initialize()
        for individual in self.population:
            individual.fitness = evaluate_fn(individual.hyperparameters)
            individual.step += 1
        self.population.sort(key=lambda ind: ind.fitness, reverse=True)
        cutoff = max(1, int(self.population_size * self.exploit_factor))
        top_k = self.population[:cutoff]
        for individual in self.population[cutoff:]:
            parent = random.choice(top_k)
            individual.hyperparameters = dict(parent.hyperparameters)
            for spec in self.hyperparameters:
                if random.random() < self.explore_factor:
                    current = individual.hyperparameters[spec.name]
                    noise = random.gauss(0, 0.1 * (spec.high - spec.low))
                    value = current + noise
                    value = max(spec.low, min(spec.high, value))
                    if spec.dtype == "int":
                        value = int(round(value))
                    individual.hyperparameters[spec.name] = value
        self.generation += 1
        best = self.population[0]
        return {
            "generation": self.generation,
            "best_fitness": best.fitness,
            "best_hyperparameters": best.hyperparameters,
            "mean_fitness": sum(ind.fitness for ind in self.population) / len(self.population),
        }


class BayesianOptimizer:
    def __init__(self, hyperparameters: list[HyperparameterSpec]):
        self.hyperparameters = hyperparameters
        self.observations: list[tuple[dict[str, Any], float]] = []

    def suggest(self) -> dict[str, Any]:
        if len(self.observations) < 2:
            values: dict[str, Any] = {}
            for spec in self.hyperparameters:
                value = random.uniform(spec.low, spec.high)
                if spec.dtype == "int":
                    value = int(round(value))
                values[spec.name] = value
            return values
        best_x, best_y = max(self.observations, key=lambda item: item[1])
        values = dict(best_x)
        for spec in self.hyperparameters:
            if random.random() < 0.3:
                value = values[spec.name] + random.gauss(0, 0.1 * (spec.high - spec.low))
                value = max(spec.low, min(spec.high, value))
                if spec.dtype == "int":
                    value = int(round(value))
                values[spec.name] = value
        return values

    def observe(self, hyperparameters: dict[str, Any], fitness: float) -> None:
        self.observations.append((dict(hyperparameters), fitness))
