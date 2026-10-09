import numpy as np
from typing import List, Tuple, Optional, Callable


class Fish:
    def __init__(self, bounds: List[Tuple[float, float]], rng: np.random.Generator):
        self.bounds = bounds
        self.position = np.array([rng.uniform(low, high) for low, high in bounds])
        self.weight = rng.uniform(1.0, 2.0)
        self.best_position = self.position.copy()
        self.best_fitness: float = float("inf")
        self.fitness: float = float("inf")

    def evaluate(self, func: Callable[[np.ndarray], float]) -> float:
        self.fitness = float(func(self.position))
        if self.fitness < self.best_fitness:
            self.best_fitness = self.fitness
            self.best_position = self.position.copy()
        return self.fitness

    def feeding(self, step_individual: float) -> None:
        if self.best_fitness < self.fitness:
            direction = self.best_position - self.position
            norm = np.linalg.norm(direction)
            if norm > 1e-9:
                self.position += step_individual * direction / norm
        for i, (low, high) in enumerate(self.bounds):
            self.position[i] = np.clip(self.position[i], low, high)

    def swimming(self, barycenter: np.ndarray, step_volitive: float) -> None:
        direction = barycenter - self.position
        norm = np.linalg.norm(direction)
        if norm > 1e-9:
            self.position += step_volitive * direction / norm
        for i, (low, high) in enumerate(self.bounds):
            self.position[i] = np.clip(self.position[i], low, high)

    def update_weight(self, delta: float) -> None:
        self.weight = max(1.0, self.weight + delta)


class FishSchoolSearch:
    def __init__(
        self,
        func: Callable[[np.ndarray], float],
        bounds: List[Tuple[float, float]],
        n_fish: int = 30,
        step_individual: float = 0.1,
        step_volitive: float = 0.2,
        seed: Optional[int] = None,
    ):
        self.func = func
        self.bounds = bounds
        self.step_individual = step_individual
        self.step_volitive = step_volitive
        self.rng = np.random.default_rng(seed)
        self.fish = [Fish(bounds, self.rng) for _ in range(n_fish)]
        for f in self.fish:
            f.evaluate(func)
        self.best_fish = min(self.fish, key=lambda f: f.fitness)
        self.history: List[float] = [self.best_fish.fitness]

    def step(self) -> None:
        positions = np.vstack([f.position for f in self.fish])
        weights = np.array([f.weight for f in self.fish])
        barycenter = np.sum(positions * weights[:, None], axis=0) / np.sum(weights)
        prev_avg_weight = float(np.mean(weights))
        for f in self.fish:
            f.feeding(self.step_individual)
        for f in self.fish:
            f.swimming(barycenter, self.step_volitive)
        for f in self.fish:
            f.evaluate(self.func)
        curr_avg_weight = float(np.mean([f.weight for f in self.fish]))
        delta = 1.0 if curr_avg_weight > prev_avg_weight else -1.0
        for f in self.fish:
            f.update_weight(delta)
        if curr_avg_weight > prev_avg_weight:
            direction = barycenter - positions
            norms = np.linalg.norm(direction, axis=1, keepdims=True)
            mask = norms > 1e-9
            direction = np.where(mask, direction / norms, 0.0)
            for i, f in enumerate(self.fish):
                f.position += self.step_volitive * direction[i].flatten()
                for j, (low, high) in enumerate(self.bounds):
                    f.position[j] = np.clip(f.position[j], low, high)
                f.evaluate(self.func)
        else:
            direction = positions - barycenter
            norms = np.linalg.norm(direction, axis=1, keepdims=True)
            mask = norms > 1e-9
            direction = np.where(mask, direction / norms, 0.0)
            for i, f in enumerate(self.fish):
                f.position += self.step_volitive * direction[i].flatten()
                for j, (low, high) in enumerate(self.bounds):
                    f.position[j] = np.clip(f.position[j], low, high)
                f.evaluate(self.func)
        self.best_fish = min(self.fish, key=lambda f: f.fitness)
        self.history.append(self.best_fish.fitness)

    def optimize(self, iterations: int) -> Tuple[np.ndarray, float, List[float]]:
        for _ in range(iterations):
            self.step()
        return self.best_fish.position.copy(), self.best_fish.fitness, self.history
