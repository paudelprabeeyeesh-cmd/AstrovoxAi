import numpy as np
from typing import List, Tuple, Optional


class Bird:
    def __init__(self, bird_id: int, position: np.ndarray, velocity: np.ndarray):
        self.bird_id = bird_id
        self.position = position.copy()
        self.velocity = velocity.copy()
        self.is_leader = False
        self.slot: Optional[int] = None

    def update(self, acceleration: np.ndarray, dt: float = 1.0) -> None:
        self.velocity += acceleration * dt
        speed = np.linalg.norm(self.velocity)
        if speed > 10.0:
            self.velocity = self.velocity / speed * 10.0
        if speed < 0.5:
            self.velocity = self.velocity / max(speed, 1e-6) * 0.5
        self.position += self.velocity * dt


class VFormationFlocking:
    def __init__(self, n_birds: int, separation: float = 3.0, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed)
        self.separation = separation
        self.birds: List[Bird] = []
        self.leader_idx = 0
        for i in range(n_birds):
            pos = np.array([0.0, i * separation])
            vel = np.array([1.0, 0.0])
            bird = Bird(i, pos, vel)
            if i == 0:
                bird.is_leader = True
                bird.slot = 0
            else:
                bird.is_leader = False
                side = 1 if i % 2 == 1 else -1
                row = (i + 1) // 2
                bird.slot = row
                bird.position = np.array([side * separation * 0.6, row * separation])
            self.birds.append(bird)
        self.wake_history: List[float] = []

    def _leader_force(self) -> np.ndarray:
        leader = self.birds[self.leader_idx]
        accel = np.zeros(2)
        accel[0] += 0.05
        if leader.position[0] > 50.0:
            accel[0] -= 0.1
        return accel

    def _formation_force(self, bird: Bird) -> np.ndarray:
        target = self._target_position(bird)
        desired = target - bird.position
        dist = np.linalg.norm(desired)
        if dist > 1e-6:
            desired = desired / dist * 2.0
        return desired - bird.velocity

    def _target_position(self, bird: Bird) -> np.ndarray:
        if bird.is_leader:
            return np.array([0.0, 0.0])
        side = 1 if bird.bird_id % 2 == 1 else -1
        row = bird.slot if bird.slot is not None else 1
        return np.array([side * self.separation * 0.6, row * self.separation])

    def _separation_force(self, bird: Bird) -> np.ndarray:
        steering = np.zeros(2)
        for other in self.birds:
            if other is bird:
                continue
            diff = bird.position - other.position
            dist = np.linalg.norm(diff)
            if 0 < dist < self.separation * 0.8:
                steering += diff / max(dist, 1e-6)
        return steering * 0.5

    def step(self, dt: float = 1.0) -> None:
        leader_force = self._leader_force()
        for bird in self.birds:
            formation = self._formation_force(bird)
            separation = self._separation_force(bird)
            accel = leader_force if bird.is_leader else formation
            accel += separation
            bird.update(accel, dt=dt)

    def rotate_leader(self) -> None:
        self.birds[self.leader_idx].is_leader = False
        self.leader_idx = (self.leader_idx + 1) % len(self.birds)
        self.birds[self.leader_idx].is_leader = True

    def formation_quality(self) -> float:
        if len(self.birds) < 2:
            return 1.0
        errors = []
        for bird in self.birds:
            if bird.is_leader:
                continue
            target = self._target_position(bird)
            errors.append(np.linalg.norm(bird.position - target))
        avg_error = float(np.mean(errors))
        quality = 1.0 / (1.0 + avg_error)
        self.wake_history.append(quality)
        return quality
