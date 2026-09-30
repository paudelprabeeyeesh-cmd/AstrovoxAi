"""Learning rate schedules.

Schedules matter as much as the optimizer in practice. A constant rate either
stalls early or destabilizes late; annealing the rate lets the model settle
into a minimum instead of oscillating around it.
"""

from __future__ import annotations

import math
from typing import Any, Callable


class LRScheduler:
    """Base class for schedules.

    Schedules hold a reference to the optimizer and set ``optimizer.lr`` on
    every :meth:`step`, so a scheduler never needs to be threaded through the
    training loop separately.
    """

    def __init__(self, optimizer: Any, last_epoch: int = -1) -> None:
        self.optimizer = optimizer
        self.last_epoch = last_epoch
        self.step(0)

    def step(self, epoch: int | None = None) -> float:
        """Advance the schedule and apply the new rate; returns it."""
        if epoch is None:
            self.last_epoch += 1
        else:
            self.last_epoch = epoch
        rate = self.get_lr()
        self.optimizer.lr = rate
        return rate

    def get_lr(self) -> float:
        """Return the rate for the current step. Subclasses override this."""
        return getattr(self.optimizer, "lr", 0.0)

    def state_dict(self) -> dict[str, Any]:
        """Return schedule state for checkpointing."""
        return {"type": type(self).__name__, "last_epoch": self.last_epoch}

    def load_state_dict(self, data: dict[str, Any]) -> None:
        """Restore schedule state."""
        self.last_epoch = data.get("last_epoch", -1)
        self.step(self.last_epoch)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(last_epoch={self.last_epoch}, lr={getattr(self.optimizer, 'lr', 0):.6g})"


class ConstantLR(LRScheduler):
    """Hold the learning rate fixed."""

    def __init__(self, optimizer: Any, factor: float = 1.0, last_epoch: int = -1) -> None:
        self.factor = factor
        self.base_lr = getattr(optimizer, "lr", 0.0)
        super().__init__(optimizer, last_epoch)

    def get_lr(self) -> float:
        """Return the constant rate."""
        return self.base_lr * self.factor


class StepLR(LRScheduler):
    """Multiply the rate by ``gamma`` every ``step_size`` epochs."""

    def __init__(self, optimizer: Any, step_size: int, gamma: float = 0.1, last_epoch: int = -1) -> None:
        if step_size < 1:
            raise ValueError(f"step_size must be at least 1, got {step_size}")
        self.step_size = step_size
        self.gamma = gamma
        self.base_lr = getattr(optimizer, "lr", 0.0)
        super().__init__(optimizer, last_epoch)

    def get_lr(self) -> float:
        """Decay once per ``step_size`` epochs."""
        return self.base_lr * (self.gamma ** (self.last_epoch // self.step_size))


class ExponentialLR(LRScheduler):
    """Multiply the rate by ``gamma`` after every epoch."""

    def __init__(self, optimizer: Any, gamma: float = 0.95, last_epoch: int = -1) -> None:
        self.gamma = gamma
        self.base_lr = getattr(optimizer, "lr", 0.0)
        super().__init__(optimizer, last_epoch)

    def get_lr(self) -> float:
        """Decay every epoch."""
        return self.base_lr * (self.gamma**self.last_epoch)


class CosineAnnealingLR(LRScheduler):
    """Anneal the rate along a cosine curve down to ``eta_min``.

    This is the standard schedule for pretraining: it keeps the rate high
    while there is still progress, then eases off so the run converges.
    """

    def __init__(
        self,
        optimizer: Any,
        t_max: int,
        eta_min: float = 0.0,
        last_epoch: int = -1,
    ) -> None:
        if t_max < 1:
            raise ValueError(f"t_max must be at least 1, got {t_max}")
        self.t_max = t_max
        self.eta_min = eta_min
        self.base_lr = getattr(optimizer, "lr", 0.0)
        super().__init__(optimizer, last_epoch)

    def get_lr(self) -> float:
        """Return the cosine-annealed rate."""
        progress = self.last_epoch / self.t_max
        return self.eta_min + (self.base_lr - self.eta_min) * 0.5 * (1.0 + math.cos(math.pi * progress))


class OneCycleLR(LRScheduler):
    """Warm up to ``max_lr`` then anneal down, optionally with a second rise.

    The schedule packs the most learning per unit of compute, which is why it
    is the default in many fast-training recipes.
    """

    def __init__(
        self,
        optimizer: Any,
        max_lr: float,
        total_steps: int,
        pct_start: float = 0.3,
        anneal_strategy: str = "cos",
        last_epoch: int = -1,
    ) -> None:
        if not 0.0 < pct_start < 1.0:
            raise ValueError(f"pct_start must be in (0, 1), got {pct_start}")
        if total_steps < 2:
            raise ValueError(f"total_steps must be at least 2, got {total_steps}")
        self.max_lr = max_lr
        self.total_steps = total_steps
        self.pct_start = pct_start
        self.anneal_strategy = anneal_strategy
        self.min_lr = max_lr / 25.0
        self.base_lr = getattr(optimizer, "lr", max_lr)
        super().__init__(optimizer, last_epoch)

    def get_lr(self) -> float:
        """Return the one-cycle rate for the current step."""
        if self.anneal_strategy == "linear":
            return self._linear()
        return self._cosine()

    def _phase_position(self) -> tuple[float, bool]:
        """Return ``(0..1 position, is_warmup)`` for the current step."""
        step = self.last_epoch + 1
        warmup_steps = max(1, int(self.total_steps * self.pct_start))
        if step <= warmup_steps:
            return step / warmup_steps, True
        decay_steps = max(1, self.total_steps - warmup_steps)
        return min(1.0, (step - warmup_steps) / decay_steps), False

    def _cosine(self) -> float:
        position, warming = self._phase_position()
        if warming:
            return self.min_lr + (self.max_lr - self.min_lr) * position
        return self.eta_min_cosine(position)

    def _linear(self) -> float:
        position, warming = self._phase_position()
        if warming:
            return self.min_lr + (self.max_lr - self.min_lr) * position
        return self.max_lr - (self.max_lr - self.min_lr) * position

    def eta_min_cosine(self, position: float) -> float:
        """Cosine-interpolate from ``max_lr`` down to ``min_lr``."""
        return self.min_lr + 0.5 * (self.max_lr - self.min_lr) * (1.0 + math.cos(math.pi * position))

    def __repr__(self) -> str:
        return f"OneCycleLR(max_lr={self.max_lr}, total_steps={self.total_steps}, pct_start={self.pct_start})"


class LinearWarmupLR(LRScheduler):
    """Warm up linearly from ``start_factor`` then hand off to a main schedule.

    Transformers often diverge without warmup because the adaptive statistics
    in Adam are meaningless during the first few steps.

    Args:
        optimizer: the optimizer whose rate is scheduled.
        warmup_steps: number of steps spent warming up.
        start_factor: rate multiplier at step 0.
        main_scheduler: optional schedule taking over after warmup.
    """

    def __init__(
        self,
        optimizer: Any,
        warmup_steps: int,
        start_factor: float = 0.0,
        main_scheduler: LRScheduler | None = None,
    ) -> None:
        if warmup_steps < 0:
            raise ValueError(f"warmup_steps must be non-negative, got {warmup_steps}")
        if not 0.0 <= start_factor <= 1.0:
            raise ValueError(f"start_factor must be in [0, 1], got {start_factor}")
        self.warmup_steps = warmup_steps
        self.start_factor = start_factor
        self.main_scheduler = main_scheduler
        self.base_lr = getattr(optimizer, "lr", 0.0)
        super().__init__(optimizer, -1)

    def get_lr(self) -> float:
        """Return the warmup rate, or the main schedule's rate once past it."""
        if self.last_epoch < self.warmup_steps:
            if self.warmup_steps == 0:
                progress = 1.0
            else:
                progress = (self.last_epoch + 1) / self.warmup_steps
            return self.base_lr * (self.start_factor + (1.0 - self.start_factor) * progress)
        if self.main_scheduler is not None:
            return self.main_scheduler.get_lr()
        return self.base_lr


class PlateauLR(LRScheduler):
    """Reduce the rate when validation loss stops improving.

    The schedule reacts to measured progress instead of a fixed plan, which
    suits training runs whose length cannot be predicted in advance.
    """

    def __init__(
        self,
        optimizer: Any,
        patience: int = 5,
        factor: float = 0.5,
        min_lr: float = 1e-6,
        threshold: float = 1e-4,
    ) -> None:
        if patience < 1:
            raise ValueError(f"patience must be at least 1, got {patience}")
        if not 0.0 < factor < 1.0:
            raise ValueError(f"factor must be in (0, 1), got {factor}")
        self.patience = patience
        self.factor = factor
        self.min_lr = min_lr
        self.threshold = threshold
        self.base_lr = getattr(optimizer, "lr", 0.0)
        self.best: float | None = None
        self.bad_epochs = 0
        super().__init__(optimizer, -1)

    def get_lr(self) -> float:
        """Return the current rate, decaying when the plateau is reached."""
        return self.base_lr

    def report(self, metric: float) -> float:
        """Feed a validation metric in and get the possibly-updated rate."""
        if self.best is None or metric < self.best - self.threshold:
            self.best = metric
            self.bad_epochs = 0
        else:
            self.bad_epochs += 1
            if self.bad_epochs >= self.patience:
                self.base_lr = max(self.base_lr * self.factor, self.min_lr)
                self.bad_epochs = 0
        self.optimizer.lr = self.base_lr
        return self.base_lr


def build_scheduler(name: str, optimizer: Any, **kwargs: Any) -> LRScheduler:
    """Construct a schedule by name, for use from configuration files."""
    table: dict[str, Callable[[], LRScheduler]] = {
        "constant": ConstantLR,
        "step": StepLR,
        "exponential": ExponentialLR,
        "cosine": CosineAnnealingLR,
        "one_cycle": OneCycleLR,
        "plateau": PlateauLR,
        "warmup": LinearWarmupLR,
    }
    if name not in table:
        raise KeyError(f"Unknown scheduler {name!r}. Available: {sorted(table)}")
    return table[name](optimizer, **kwargs)
