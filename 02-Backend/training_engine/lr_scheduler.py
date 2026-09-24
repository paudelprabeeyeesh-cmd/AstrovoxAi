import math
from typing import List, Optional


class LRScheduler:
    def __init__(self, optimizer: "MockOptimizer", config: "TrainConfig") -> None:
        self.optimizer = optimizer
        self.lr = float(config.learning_rate)
        self.warmup_steps = int(config.warmup_steps)
        self.max_steps = int(config.max_steps)
        self.min_lr = float(config.min_lr)
        self.step_count = 0

    def step(self) -> float:
        self.step_count += 1
        lr = self._compute_lr()
        self.optimizer.set_lr(lr)
        return lr

    def get_lr(self) -> float:
        return self._compute_lr()

    def _compute_lr(self) -> float:
        if self.step_count == 0:
            return self.lr
        if self.step_count <= self.warmup_steps:
            return self.lr * self.step_count / max(self.warmup_steps, 1)
        progress = (self.step_count - self.warmup_steps) / max(self.max_steps - self.warmup_steps, 1)
        progress = min(progress, 1.0)
        cosine = 0.5 * (1.0 + math.cos(math.pi * progress))
        return self.min_lr + (self.lr - self.min_lr) * cosine


class MockOptimizer:
    def __init__(self) -> None:
        self.lr = 0.0

    def set_lr(self, value: float) -> None:
        self.lr = float(value)


class TrainConfig:
    def __init__(
        self,
        learning_rate: float = 1e-3,
        warmup_steps: int = 0,
        max_steps: int = 1000,
        min_lr: float = 0.0,
    ) -> None:
        self.learning_rate = float(learning_rate)
        self.warmup_steps = int(warmup_steps)
        self.max_steps = int(max_steps)
        self.min_lr = float(min_lr)
