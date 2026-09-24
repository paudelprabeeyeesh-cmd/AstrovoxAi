import numpy as np
from typing import List, Optional


class ProjectionHead:
    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 256,
        output_dim: int = 128,
        seed: Optional[int] = None,
    ):
        if seed is not None:
            rng = np.random.default_rng(seed)
        else:
            rng = np.random.default_rng()

        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim

        self.W1 = rng.standard_normal((input_dim, hidden_dim)).astype(np.float64) * np.sqrt(2.0 / input_dim)
        self.b1 = np.zeros(hidden_dim, dtype=np.float64)
        self.W2 = rng.standard_normal((hidden_dim, output_dim)).astype(np.float64) * np.sqrt(2.0 / hidden_dim)
        self.b2 = np.zeros(output_dim, dtype=np.float64)

        self.params: List[np.ndarray] = [self.W1, self.b1, self.W2, self.b2]

    @staticmethod
    def _relu(x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)

    def forward(self, x: np.ndarray) -> np.ndarray:
        h = self._relu(x @ self.W1 + self.b1)
        z = h @ self.W2 + self.b2
        return z

    def __call__(self, x: np.ndarray) -> np.ndarray:
        return self.forward(x)
