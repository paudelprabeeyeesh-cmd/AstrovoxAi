import math
import random
from differential_privacy.typing import DPParams


class LaplaceMechanism:
    def __init__(self, sensitivity: float, epsilon: float):
        self.sensitivity = sensitivity
        self.epsilon = epsilon
        self.b = sensitivity / epsilon

    def release(self, value: float) -> float:
        u = random.random()
        if u < 0.5:
            return value + self.b * math.log(2 * u)
        else:
            return value - self.b * math.log(2 - 2 * u)

    def budget(self) -> DPParams:
        return DPParams(epsilon=self.epsilon, delta=0.0)
