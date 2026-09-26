import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ArchitectureCandidate:
    candidate_id: str
    layers: list[dict[str, Any]]
    parameters: int
    fitness: float = 0.0
    generation: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class EvolutionaryArchitectureService:
    def __init__(self) -> None:
        self._population: dict[str, ArchitectureCandidate] = {}
        self._history: list[dict[str, Any]] = []
        self._client = None
        self._max_parameters = 10000000

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def initialize(self, population_size: int = 10) -> list[dict[str, Any]]:
        population = []
        for i in range(population_size):
            candidate_id = f"arch_{uuid.uuid4().hex[:8]}"
            layers = [
                {"type": "dense", "units": 64, "activation": "relu"},
                {"type": "dense", "units": 32, "activation": "relu"},
                {"type": "dense", "units": 1, "activation": "sigmoid"},
            ]
            params = sum(layer.get("units", 0) for layer in layers)
            candidate = ArchitectureCandidate(candidate_id=candidate_id, layers=layers, parameters=params, generation=0)
            self._population[candidate_id] = candidate
            population.append(self._candidate_to_dict(candidate))
        logger.info("Initialized architecture population with %d candidates", population_size)
        return population

    def evolve(self, population: list[dict[str, Any]], fitness_scores: list[float]) -> list[dict[str, Any]]:
        if len(population) != len(fitness_scores):
            raise ValueError("Population size must match fitness scores")

        scored = list(zip(population, fitness_scores))
        scored.sort(key=lambda x: x[1], reverse=True)
        survivors = [candidate for candidate, score in scored[: max(1, len(scored) // 2)]]

        next_gen = []
        for candidate in survivors:
            child_id = f"arch_{uuid.uuid4().hex[:8]}"
            child_layers = self._mutate_layers(candidate.get("layers", []))
            params = sum(layer.get("units", 0) for layer in child_layers)
            child = ArchitectureCandidate(
                candidate_id=child_id,
                layers=child_layers,
                parameters=params,
                fitness=candidate.get("fitness", 0.0),
                generation=candidate.get("generation", 0) + 1,
            )
            self._population[child_id] = child
            next_gen.append(self._candidate_to_dict(child))

        logger.info("Evolved population from %d to %d candidates", len(population), len(next_gen))
        return next_gen

    def evaluate(self, candidate_id: str, metrics: dict[str, float]) -> dict[str, Any]:
        candidate = self._population.get(candidate_id)
        if not candidate:
            return {"candidate_id": candidate_id, "status": "not_found"}
        candidate.fitness = float(metrics.get("fitness", candidate.fitness))
        self._history.append({"candidate_id": candidate_id, "fitness": candidate.fitness, "timestamp": time.time()})
        return {"candidate_id": candidate_id, "fitness": round(candidate.fitness, 4), "status": "evaluated"}

    def get_candidate(self, candidate_id: str) -> dict[str, Any] | None:
        candidate = self._population.get(candidate_id)
        if not candidate:
            return None
        return self._candidate_to_dict(candidate)

    def list_candidates(self) -> list[str]:
        return list(self._population.keys())

    def get_best(self, top_k: int = 5) -> list[dict[str, Any]]:
        scored = [(c.fitness, c) for c in self._population.values()]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [self._candidate_to_dict(c) for _, c in scored[:top_k]]

    def _mutate_layers(self, layers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        import random
        new_layers = []
        for layer in layers:
            new_layer = dict(layer)
            if random.random() < 0.3:
                units = new_layer.get("units", 64)
                new_layer["units"] = max(1, units + random.randint(-16, 16))
            new_layers.append(new_layer)
        return new_layers

    def _candidate_to_dict(self, candidate: ArchitectureCandidate) -> dict[str, Any]:
        return {
            "candidate_id": candidate.candidate_id,
            "layers": candidate.layers,
            "parameters": candidate.parameters,
            "fitness": candidate.fitness,
            "generation": candidate.generation,
        }
