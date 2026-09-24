import numpy as np
from typing import List, Tuple, Optional


class Fish:
    def __init__(self, bounds: List[Tuple[float, float]], rng: np.random.Generator):
        self.bounds = bounds
        self.position = np.array([rng.uniform(low, high) for low, high in bounds])
        self.weight = rng.uniform(0.5, 1.5)
        self.best_position = self.position.copy()
        self.best_fitness: float = float("inf")

    def fitness(self, func) -> float:
        return float(func(self.position))

    def feeding(self, func, step: float) -> None:
        f = self.fitness(func)
        direction = self.best_position - self.position
        norm = np.linalg.norm(direction)
        if norm > 1e-9:
            self.position += step * direction / norm * np.random.rand()
            for i, (low, high) in enumerate(self.bounds):
                self.position[i] = np.clip(self.position[i], low, high)
        f_new = self.fitness(func)
        if f_new < f:
            self.weight += f_new
        else:
            self.weight -= f_new
        self.weight = max(0.01, self.weight)

    def swimming(self, school_center: np.ndarray, step: float) -> None:
        direction = school_center - self.position
        norm = np.linalg.norm(direction)
        if norm > 1e-9:
            self.position += step * direction / norm * np.random.rand()
            for i, (low, high) in enumerate(self.bounds):
                self.position[i] = np.clip(self.position[i], low, high)

    def memory(self, func) -> None:
        f = self.fitness(func)
        if f < self.best_fitness:
            self.best_fitness = f
            self.best_position = self.position.copy()


class FishSchoolSearch:
    def __init__(
        self,
        func,
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
        self.best_fish: Optional[Fish] = None
        self.history: List[float] = []
        self._evaluate()

    def _evaluate(self) -> None:
        best = min(self.fish, key=lambda f: f.fitness(self.func))
        if self.best_fish is None or best.fitness(self.func) < self.best_fish.fitness(self.func):
            self.best_fish = best
        self.history.append(self.best_fish.fitness(self.func))

    def step(self) -> None:
        school_center = np.mean([f.position for f in self.fish], axis=0)
        total_weight = sum(f.weight for f in self.fish)
        barycenter = sum(f.weight * f.position for f in self.fish) / total_weight
        for fish in self.fish:
            fish.feeding(self.func, self.step_individual)
            fish.swimming(barycenter, self.step_volitive)
            fish.memory(self.func)
        prev_avg = total_weight / len(self.fish)
        curr_avg = sum(f.weight for f in self.fish) / len(self.fish)
        if curr_avg > prev_avg:
            direction = barycenter - school_center
            for fish in self.fish:
                norm = np.linalg.norm(direction)
                if norm > 1e-9:
                    fish.position += self.step_volitive * direction / norm * np.random.rand()
                    for i, (low, high) in enumerate(self.bounds):
                        fish.position[i] = np.clip(fish.position[i], low, high)
        else:
            direction = school_center - barycenter
            for fish in self.fish:
                norm = np.linalg.norm(direction)
                if norm > 1e-9:
                    fish.position += self.step_volitive * direction / norm * np.random.rand()
                    for i, (low, high) in enumerate(self.bounds):
                        fish.position[i] = np.clip(fish.position[i], low, high)
        self._evaluate()

    def optimize(self, iterations: int) -> Tuple[np.ndarray, float, List[float]]:
        for _ in range(iterations):
            self.step()
        assert self.best_fish is not None
        return self.best_fish.position.copy(), self.best_fish.fitness(self.func), self.history
