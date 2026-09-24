import math
import random
from typing import Dict, List


class TaskSpecificHead:
    def __init__(self, shared_dim: int, output_dim: int, seed: int = 0):
        self.shared_dim = shared_dim
        self.output_dim = output_dim
        random.seed(seed)
        scale = math.sqrt(2.0 / shared_dim)
        self.weights = [
            [random.gauss(0.0, scale) for _ in range(output_dim)]
            for _ in range(shared_dim)
        ]
        self.bias = [0.0] * output_dim

    def forward(self, h: List[float]) -> List[float]:
        out = []
        for j in range(self.output_dim):
            s = self.bias[j]
            for i in range(self.shared_dim):
                s += h[i] * self.weights[i][j]
            out.append(s)
        return out

    def get_parameters(self) -> Dict[str, List[List[float]]]:
        return {
            "weights": [row[:] for row in self.weights],
            "bias": self.bias[:],
        }
