import math
import random
from differential_privacy.typing import DPParams


class GaussianMechanism:
    def __init__(self, sensitivity: float, epsilon: float, delta: float):
        self.sensitivity = sensitivity
        self.epsilon = epsilon
        self.delta = delta
        self.sigma = math.sqrt(2 * math.log(1.25 / delta)) * sensitivity / epsilon

    def release(self, value: float) -> float:
        return value + random.gauss(0, self.sigma)

    def budget(self) -> DPParams:
        return DPParams(epsilon=self.epsilon, delta=self.delta)
