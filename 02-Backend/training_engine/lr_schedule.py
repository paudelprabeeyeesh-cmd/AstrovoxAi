import numpy as np


class CosineLRScheduler:
    def __init__(self, lr, warmup_steps, max_steps, min_lr=0.0):
        self.lr = float(lr)
        self.warmup_steps = int(warmup_steps)
        self.max_steps = int(max_steps)
        self.min_lr = float(min_lr)
        self.step_count = 0

    def step(self):
        self.step_count += 1
        return self._compute_lr()

    def get_lr(self):
        return self._compute_lr()

    def _compute_lr(self):
        if self.step_count <= self.warmup_steps:
            return self.lr * self.step_count / self.warmup_steps
        progress = (self.step_count - self.warmup_steps) / (self.max_steps - self.warmup_steps)
        progress = min(progress, 1.0)
        cosine = 0.5 * (1 + np.cos(np.pi * progress))
        return self.min_lr + (self.lr - self.min_lr) * cosine
