"""Neural Architecture Search wrappers and configurable search spaces."""

from __future__ import annotations

import logging
import random
import math
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ArchitectureCandidate:
    nodes: list[dict[str, Any]] = field(default_factory=list)
    connections: list[tuple[int, int]] = field(default_factory=list)
    fitness: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class SearchSpace:
    def __init__(
        self,
        layer_types: list[str] | None = None,
        units_range: tuple[int, int] = (16, 512),
        activations: list[str] | None = None,
        dropouts: list[float] | None = None,
    ):
        self.layer_types = layer_types or ["dense", "conv1d", "conv2d", "attention", "moe", "ssm", "linear_attn"]
        self.units_range = units_range
        self.activations = activations or ["relu", "gelu", "silu", "swish", "tanh", "sigmoid"]
        self.dropouts = dropouts or [0.0, 0.1, 0.2, 0.3, 0.5]

    def sample_layer(self) -> dict[str, Any]:
        layer_type = random.choice(self.layer_types)
        config: dict[str, Any] = {"type": layer_type}
        if layer_type in ("dense", "moe"):
            config["units"] = random.randint(*self.units_range)
        if layer_type in ("conv1d", "conv2d"):
            config["filters"] = random.randint(16, 256)
            config["kernel_size"] = random.choice([1, 3, 5, 7])
            config["stride"] = random.choice([1, 2])
        if layer_type in ("attention", "linear_attn"):
            config["heads"] = 2 ** random.randint(1, 4)
            config["dim"] = random.choice([64, 128, 256, 512])
        config["activation"] = random.choice(self.activations)
        config["dropout"] = random.choice(self.dropouts)
        return config

    def sample_candidate(self, num_layers: int = 4) -> ArchitectureCandidate:
        nodes = [self.sample_layer() for _ in range(num_layers)]
        connections = [(i, i + 1) for i in range(num_layers - 1)]
        return ArchitectureCandidate(nodes=nodes, connections=connections)


class NASController:
    def __init__(self, search_space: SearchSpace | None = None):
        self.search_space = search_space or SearchSpace()
        self.population: list[ArchitectureCandidate] = []

    def initialize_population(self, size: int = 10) -> list[ArchitectureCandidate]:
        self.population = [self.search_space.sample_candidate() for _ in range(size)]
        return self.population

    def evaluate(self, candidate: ArchitectureCandidate, metric: float) -> None:
        candidate.fitness = max(0.0, min(1.0, metric))

    def mutate(self, candidate: ArchitectureCandidate, rate: float = 0.2) -> ArchitectureCandidate:
        mutated = ArchitectureCandidate(
            nodes=[dict(n) for n in candidate.nodes],
            connections=list(candidate.connections),
            fitness=candidate.fitness,
            metadata=dict(candidate.metadata),
        )
        for node in mutated.nodes:
            if random.random() < rate:
                node.update(self.search_space.sample_layer())
        if random.random() < rate and len(mutated.nodes) > 1:
            idx = random.randint(0, len(mutated.connections) - 1)
            mutated.connections[idx] = (mutated.connections[idx][0], mutated.connections[idx][1] + random.choice([-1, 1]))
        return mutated

    def crossover(self, a: ArchitectureCandidate, b: ArchitectureCandidate) -> ArchitectureCandidate:
        split = random.randint(1, min(len(a.nodes), len(b.nodes)) - 1)
        child_nodes = a.nodes[:split] + b.nodes[split:]
        child_connections = [(i, i + 1) for i in range(len(child_nodes) - 1)]
        return ArchitectureCandidate(nodes=child_nodes, connections=child_connections)

    def select(self, num: int = 2) -> list[ArchitectureCandidate]:
        if not self.population:
            return []
        weights = [max(candidate.fitness, 1e-6) for candidate in self.population]
        total = sum(weights)
        if total == 0:
            selected = random.choices(self.population, k=num)
        else:
            probs = [w / total for w in weights]
            selected = random.choices(self.population, weights=weights, k=num)
        return selected

    def evolve_generation(self) -> dict[str, Any]:
        if not self.population:
            return {"population_size": 0, "best_fitness": 0.0}
        elite = max(self.population, key=lambda c: c.fitness)
        new_pop = [elite]
        while len(new_pop) < len(self.population):
            parents = self.select(2)
            child = self.crossover(parents[0], parents[1])
            child = self.mutate(child)
            new_pop.append(child)
        self.population = new_pop
        best = max(self.population, key=lambda c: c.fitness)
        return {
            "population_size": len(self.population),
            "best_fitness": best.fitness,
            "mean_fitness": sum(c.fitness for c in self.population) / len(self.population),
            "best_nodes": best.nodes,
        }


class ENASController:
    def __init__(self, num_nodes: int = 4, num_ops: int = 5):
        self.num_nodes = num_nodes
        self.num_ops = num_ops
        self._alphas = [[0.0] * num_ops for _ in range(num_nodes)]

    def sample_architecture(self) -> list[int]:
        return [max(range(self.num_ops), key=lambda op: self._alphas[node][op] + random.gauss(0, 0.1)) for node in range(self.num_nodes)]

    def update_alphas(self, rewards: list[float], architectures: list[list[int]], lr: float = 0.01) -> None:
        for reward, arch in zip(rewards, architectures):
            for node, op in enumerate(arch):
                grad = reward * (1.0 - math.exp(-self._alphas[node][op]))
                self._alphas[node][op] += lr * grad
