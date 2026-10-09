import random
from typing import List, Sequence, Callable, Optional


class SGD:
    def __init__(self, params: List[float], lr: float = 0.01) -> None:
        self.params = list(params)
        self.lr = float(lr)

    def step(self, grads: List[float]) -> List[float]:
        for i, (p, g) in enumerate(zip(self.params, grads)):
            self.params[i] = p - self.lr * g
        return list(self.params)
