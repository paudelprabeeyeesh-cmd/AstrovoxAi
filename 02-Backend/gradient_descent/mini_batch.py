import random
from typing import List, Callable, Optional
from .sgd import SGD


class MiniBatchGradientDescent:
    def __init__(
        self,
        params: List[float],
        x: List[List[float]],
        y: List[float],
        loss_fn: Callable[[List[float], List[List[float]], List[float]], float],
        grad_fn: Callable[[List[float], List[List[float]], List[float]], List[float]],
        batch_size: int = 32,
        lr: float = 0.01,
        epochs: int = 100,
        tol: float = 1e-6,
        shuffle: bool = True,
    ) -> None:
        self.params = list(params)
        self.x = [list(row) for row in x]
        self.y = list(y)
        self.loss_fn = loss_fn
        self.grad_fn = grad_fn
        self.batch_size = int(batch_size)
        self.lr = float(lr)
        self.epochs = int(epochs)
        self.tol = float(tol)
        self.shuffle = bool(shuffle)
        self.loss_history: List[float] = []

    def fit(self) -> List[float]:
        opt = SGD(self.params, lr=self.lr)
        prev_loss = self.loss_fn(opt.params, self.x, self.y)
        self.loss_history.append(prev_loss)
        for _ in range(self.epochs):
            indices = list(range(len(self.x)))
            if self.shuffle:
                random.shuffle(indices)
            x_shuffled = [self.x[i] for i in indices]
            y_shuffled = [self.y[i] for i in indices]
            for start in range(0, len(self.x), self.batch_size):
                xb = x_shuffled[start:start + self.batch_size]
                yb = y_shuffled[start:start + self.batch_size]
                g = self.grad_fn(opt.params, xb, yb)
                opt.step(g)
            loss = self.loss_fn(opt.params, self.x, self.y)
            self.loss_history.append(loss)
            if abs(prev_loss - loss) < self.tol:
                break
            prev_loss = loss
        self.params = opt.params
        return list(self.params)
