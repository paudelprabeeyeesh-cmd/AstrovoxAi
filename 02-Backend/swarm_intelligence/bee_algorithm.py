import numpy as np
from typing import Callable, List, Tuple, Optional


class FoodSource:
    def __init__(self, position: np.ndarray, fitness: float):
        self.position = position.copy()
        self.fitness = fitness
        self.trials = 0
        self.probability: float = 0.0

    def abandon(self, limit: int) -> bool:
        return self.trials >= limit


class BeeColonyOptimization:
    def __init__(
        self,
        func: Callable[[np.ndarray], float],
        bounds: List[Tuple[float, float]],
        n_bees: int = 30,
        limit: int = 100,
        seed: Optional[int] = None,
    ):
        self.func = func
        self.bounds = bounds
        self.n_bees = n_bees
        self.limit = limit
        self.rng = np.random.default_rng(seed)
        half = n_bees // 2
        self.sources = [self._random_source() for _ in range(half)]
        self.best_source: Optional[FoodSource] = None
        self._evaluate_sources()

    def _random_source(self) -> FoodSource:
        pos = np.array([self.rng.uniform(low, high) for low, high in self.bounds])
        fitness = self._fitness(pos)
        return FoodSource(pos, fitness)

    def _fitness(self, position: np.ndarray) -> float:
        val = self.func(position)
        return 1.0 / (1.0 + val) if val >= 0 else 1.0 + abs(val)

    def _evaluate_sources(self) -> None:
        for source in self.sources:
            source.fitness = self._fitness(source.position)
        self.best_source = max(self.sources, key=lambda s: s.fitness)

    def _employed_phase(self) -> None:
        for source in self.sources:
            partner = self.rng.choice(self.sources)
            if partner is source:
                continue
            idx = self.rng.integers(0, len(source.position))
            new_pos = source.position.copy()
            new_pos[idx] += self.rng.uniform(-1, 1) * (source.position[idx] - partner.position[idx])
            for i, (low, high) in enumerate(self.bounds):
                new_pos[i] = np.clip(new_pos[i], low, high)
            new_fit = self._fitness(new_pos)
            if new_fit > source.fitness:
                source.position = new_pos
                source.fitness = new_fit
                source.trials = 0
            else:
                source.trials += 1

    def _onlooker_phase(self) -> None:
        total = sum(s.fitness for s in self.sources)
        if total == 0:
            probs = [1.0 / len(self.sources)] * len(self.sources)
        else:
            probs = [s.fitness / total for s in self.sources]
        for _ in range(self.n_bees // 2):
            idx = self.rng.choice(len(self.sources), p=probs)
            source = self.sources[idx]
            partner = self.rng.choice(self.sources)
            if partner is source:
                continue
            dim = self.rng.integers(0, len(source.position))
            new_pos = source.position.copy()
            new_pos[dim] += self.rng.uniform(-1, 1) * (source.position[dim] - partner.position[dim])
            for i, (low, high) in enumerate(self.bounds):
                new_pos[i] = np.clip(new_pos[i], low, high)
            new_fit = self._fitness(new_pos)
            if new_fit > source.fitness:
                source.position = new_pos
                source.fitness = new_fit
                source.trials = 0
            else:
                source.trials += 1

    def _scout_phase(self) -> None:
        for source in self.sources:
            if source.abandon(self.limit):
                source = self._random_source()
                source.trials = 0

    def step(self) -> None:
        self._employed_phase()
        self._onlooker_phase()
        self._scout_phase()
        self._evaluate_sources()

    def optimize(self, iterations: int) -> Tuple[np.ndarray, float, List[float]]:
        history = []
        for _ in range(iterations):
            self.step()
            assert self.best_source is not None
            history.append(self.best_source.fitness)
        return self.best_source.position.copy(), 1.0 / self.best_source.fitness - 1.0, history
