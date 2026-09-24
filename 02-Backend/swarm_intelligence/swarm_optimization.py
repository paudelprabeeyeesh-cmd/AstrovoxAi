import numpy as np
from typing import Callable, List, Tuple, Optional


class Particle:
    def __init__(self, bounds: List[Tuple[float, float]], rng: np.random.Generator):
        self.bounds = bounds
        self.position = np.array([rng.uniform(low, high) for low, high in bounds])
        self.velocity = np.array([rng.uniform(-1, 1) for _ in bounds])
        self.best_position = self.position.copy()
        self.best_fitness: float = float("inf")

    def update(self, global_best: np.ndarray, w: float, c1: float, c2: float) -> None:
        r1 = np.random.rand(len(self.position))
        r2 = np.random.rand(len(self.position))
        cognitive = c1 * r1 * (self.best_position - self.position)
        social = c2 * r2 * (global_best - self.position)
        self.velocity = w * self.velocity + cognitive + social
        for i, (low, high) in enumerate(self.bounds):
            if self.position[i] + self.velocity[i] < low:
                self.velocity[i] *= -0.5
            elif self.position[i] + self.velocity[i] > high:
                self.velocity[i] *= -0.5
        self.position += self.velocity
        for i, (low, high) in enumerate(self.bounds):
            self.position[i] = np.clip(self.position[i], low, high)


class SwarmOptimization:
    def __init__(
        self,
        func: Callable[[np.ndarray], float],
        bounds: List[Tuple[float, float]],
        n_particles: int = 30,
        w: float = 0.7,
        c1: float = 1.5,
        c2: float = 1.5,
        seed: Optional[int] = None,
    ):
        self.func = func
        self.bounds = bounds
        self.n_particles = n_particles
        self.w = w
        self.c1 = c1
        self.c2 = c2
        self.rng = np.random.default_rng(seed)
        self.particles = [Particle(bounds, self.rng) for _ in range(n_particles)]
        self.global_best: Optional[np.ndarray] = None
        self.global_best_fitness: float = float("inf")
        self.history: List[float] = []
        self._evaluate_all()

    def _evaluate_all(self) -> None:
        for p in self.particles:
            fitness = self.func(p.position)
            if fitness < p.best_fitness:
                p.best_fitness = fitness
                p.best_position = p.position.copy()
            if fitness < self.global_best_fitness:
                self.global_best_fitness = fitness
                self.global_best = p.position.copy()
        self.history.append(self.global_best_fitness)

    def step(self) -> None:
        if self.global_best is None:
            raise RuntimeError("Swarm not initialized")
        for p in self.particles:
            p.update(self.global_best, self.w, self.c1, self.c2)
        self._evaluate_all()

    def optimize(self, iterations: int) -> Tuple[np.ndarray, float, List[float]]:
        for _ in range(iterations):
            self.step()
        assert self.global_best is not None
        return self.global_best.copy(), self.global_best_fitness, self.history
