import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass
class Boid:
    position: np.ndarray
    velocity: np.ndarray
    max_speed: float = 4.0
    max_force: float = 0.1
    perception_radius: float = 5.0
    separation_radius: float = 2.0

    def edges(self, width: float, height: float) -> np.ndarray:
        if self.position[0] > width:
            self.position[0] = 0.0
        elif self.position[0] < 0.0:
            self.position[0] = width
        if self.position[1] > height:
            self.position[1] = 0.0
        elif self.position[1] < 0.0:
            self.position[1] = height
        return self.position

    def flock(self, boids: List["Boid"], weights: Tuple[float, float, float]) -> np.ndarray:
        separation = self._separation(boids) * weights[0]
        alignment = self._alignment(boids) * weights[1]
        cohesion = self._cohesion(boids) * weights[2]
        steering = separation + alignment + cohesion
        self._limit_force(steering)
        return steering

    def _separation(self, boids: List["Boid"]) -> np.ndarray:
        steering = np.zeros(2, dtype=float)
        total = 0
        for other in boids:
            if other is self:
                continue
            dist = np.linalg.norm(self.position - other.position)
            if 0.0 < dist < self.separation_radius:
                diff = self.position - other.position
                diff /= dist if dist > 1e-6 else 1e-6
                steering += diff
                total += 1
        if total > 0:
            steering /= total
            norm = np.linalg.norm(steering)
            if norm > 0:
                steering = steering / norm * self.max_speed - self.velocity
                self._limit_force(steering)
        return steering

    def _alignment(self, boids: List["Boid"]) -> np.ndarray:
        steering = np.zeros(2, dtype=float)
        total = 0
        for other in boids:
            if other is self:
                continue
            dist = np.linalg.norm(self.position - other.position)
            if 0.0 < dist < self.perception_radius:
                steering += other.velocity
                total += 1
        if total > 0:
            steering /= total
            norm = np.linalg.norm(steering)
            if norm > 0:
                steering = steering / norm * self.max_speed - self.velocity
                self._limit_force(steering)
        return steering

    def _cohesion(self, boids: List["Boid"]) -> np.ndarray:
        center = np.zeros(2, dtype=float)
        total = 0
        for other in boids:
            if other is self:
                continue
            dist = np.linalg.norm(self.position - other.position)
            if 0.0 < dist < self.perception_radius:
                center += other.position
                total += 1
        if total > 0:
            center /= total
            desired = center - self.position
            norm = np.linalg.norm(desired)
            if norm > 0:
                desired = desired / norm * self.max_speed
            steering = desired - self.velocity
            self._limit_force(steering)
            return steering
        return np.zeros(2, dtype=float)

    def _limit_force(self, force: np.ndarray) -> None:
        norm = np.linalg.norm(force)
        if norm > self.max_force:
            force = force / norm * self.max_force

    def update(self, acceleration: np.ndarray, dt: float = 1.0) -> None:
        self.velocity += acceleration * dt
        speed = np.linalg.norm(self.velocity)
        if speed > self.max_speed:
            self.velocity = self.velocity / speed * self.max_speed
        if speed < 1e-6:
            angle = np.random.uniform(0, 2 * np.pi)
            self.velocity = np.array([np.cos(angle), np.sin(angle)], dtype=float)
        self.position += self.velocity * dt


class FlockingSimulation:
    def __init__(self, n: int, width: float, height: float, seed: Optional[int] = None):
        if seed is not None:
            np.random.seed(seed)
        self.width = width
        self.height = height
        self.boids = [
            Boid(
                position=np.random.uniform(0, [width, height]),
                velocity=np.random.uniform(-1, 1, size=2),
            )
            for _ in range(n)
        ]

    def step(self, dt: float = 1.0, weights: Tuple[float, float, float] = (1.5, 1.0, 1.0)) -> None:
        for boid in self.boids:
            acceleration = boid.flock(self.boids, weights)
            boid.update(acceleration, dt=dt)
            boid.edges(self.width, self.height)

    def positions(self) -> np.ndarray:
        return np.vstack([b.position for b in self.boids])

    def velocities(self) -> np.ndarray:
        return np.vstack([b.velocity for b in self.boids])
