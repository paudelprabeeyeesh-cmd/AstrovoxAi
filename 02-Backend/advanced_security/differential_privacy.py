import math
import random
from typing import Any, Dict, List, Optional, Tuple


class LaplaceMechanism:
    def __init__(self, epsilon: float, delta: float = 1e-5, sensitivity: float = 1.0) -> None:
        if epsilon <= 0:
            raise ValueError("Epsilon must be positive")
        self._epsilon = epsilon
        self._delta = delta
        self._sensitivity = sensitivity

    def noise(self) -> float:
        scale = self._sensitivity / self._epsilon
        u = random.random() - 0.5
        return -scale * math.copysign(1, u) * math.log(1 - 2 * abs(u))

    def add_noise(self, value: float) -> float:
        return value + self.noise()

    def clip(self, value: float, low: float, high: float) -> float:
        return max(low, min(high, value))


class GaussianMechanism:
    def __init__(self, epsilon: float, delta: float, sensitivity: float = 1.0) -> None:
        self._epsilon = epsilon
        self._delta = delta
        self._sensitivity = sensitivity

    def noise(self) -> float:
        sigma = (self._sensitivity / self._epsilon) * math.sqrt(2 * math.log(1.25 / self._delta))
        u1 = random.random()
        u2 = random.random()
        return sigma * math.sqrt(-2.0 * math.log(max(u1, 1e-8))) * math.cos(2.0 * math.pi * u2)

    def add_noise(self, value: float) -> float:
        return value + self.noise()


class SparseMechanism:
    def __init__(self, epsilon: float, sparsity: int = 1) -> None:
        self._epsilon = epsilon
        self._sparsity = sparsity

    def noise(self) -> float:
        return LaplaceMechanism(epsilon=self._epsilon).noise() if random.random() < self._sparsity else 0.0


class DifferentialPrivacy:
    def __init__(self, epsilon: float = 1.0, delta: float = 1e-5) -> None:
        self._epsilon = epsilon
        self._delta = delta

    def query(self, data: List[float], mechanism: str = "laplace") -> float:
        if not data:
            raise ValueError("Data cannot be empty")
        if mechanism == "laplace":
            mech = LaplaceMechanism(self._epsilon, self._delta)
        elif mechanism == "gaussian":
            mech = GaussianMechanism(self._epsilon, self._delta)
        else:
            raise ValueError("Unsupported mechanism")
        return mech.add_noise(sum(data))

    def histogram(self, data: List[int], bins: int) -> List[float]:
        counts = [0] * bins
        for v in data:
            idx = v % bins
            counts[idx] += 1
        return [LaplaceMechanism(self._epsilon, self._delta).add_noise(c) for c in counts]

    def attribute_value(self, value: float, clip_low: float, clip_high: float, mechanism: str = "laplace") -> float:
        mech = LaplaceMechanism(self._epsilon, self._delta)
        clipped = mech.clip(value, clip_low, clip_high)
        return mech.add_noise(clipped)
