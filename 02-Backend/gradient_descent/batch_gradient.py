import math
from typing import List, Callable, Sequence, Optional
from .sgd import SGD


class BatchGradientDescent:
    def __init__(
        self,
        params: List[float],
        loss_fn: Callable[[List[float]], float],
        grad_fn: Callable[[List[float]], List[float]],
        lr: float = 0.01,
        max_iter: int = 1000,
        tol: float = 1e-6,
    ) -> None:
        self.params = list(params)
        self.loss_fn = loss_fn
        self.grad_fn = grad_fn
        self.lr = float(lr)
        self.max_iter = int(max_iter)
        self.tol = float(tol)
        self.loss_history: List[float] = []

    def fit(self) -> List[float]:
        opt = SGD(self.params, lr=self.lr)
        prev_loss = self.loss_fn(opt.params)
        self.loss_history.append(prev_loss)
        for _ in range(self.max_iter):
            g = self.grad_fn(opt.params)
            opt.step(g)
            loss = self.loss_fn(opt.params)
            self.loss_history.append(loss)
            if abs(prev_loss - loss) < self.tol:
                break
            prev_loss = loss
        self.params = opt.params
        return list(self.params)
