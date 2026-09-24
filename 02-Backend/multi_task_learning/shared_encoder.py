import math
import random
from typing import List


class SharedEncoder:
    def __init__(self, input_dim: int, shared_dim: int, seed: int = 42):
        self.input_dim = input_dim
        self.shared_dim = shared_dim
        self.seed = seed
        random.seed(seed)
        self.weights = self._init_weights()
        self.bias = [0.0] * shared_dim

    def _init_weights(self) -> List[List[float]]:
        scale = math.sqrt(2.0 / self.input_dim)
        return [
            [random.gauss(0.0, scale) for _ in range(self.shared_dim)]
            for _ in range(self.input_dim)
        ]

    def forward(self, x: List[float]) -> List[float]:
        h = []
        for j in range(self.shared_dim):
            s = self.bias[j]
            for i in range(self.input_dim):
                s += x[i] * self.weights[i][j]
            h.append(max(0.0, s))
        return h

    def get_parameters(self) -> List[List[float]]:
        return [row[:] for row in self.weights]
