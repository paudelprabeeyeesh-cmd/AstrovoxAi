"""Mixed precision: float16 and bfloat16 training with loss scaling.

Half precision doubles the arithmetic throughput of a matmul and halves the
memory it moves, but a float16 gradient underflows once the loss is small
enough, and the update disappears silently. Static loss scaling handles that:
the loss is multiplied by a fixed factor before the backward pass so the
gradients stay in range, and the factor is halved whenever an update produces
a non-finite gradient. A step that goes non-finite is skipped and the factor
halved again, so a run recovers instead of diverging.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np

from astrovox.autograd.engine import grad_norm
from astrovox.tensor.dtype import BFLOAT16, FLOAT16, DType, resolve
from astrovox.tensor.tensor import Tensor


@dataclass
class GradScaler:
    """Static loss scaling with a skip on non-finite gradients.

    Attributes:
        scale: the factor the loss is multiplied by before backward.
        growth_interval: successful steps before the scale is doubled.
        backoff_factor: factor applied when a step is skipped.
        max_scale: ceiling, so the scale cannot grow without bound.
    """

    scale: float = 65536.0
    growth_tracker: int = 0
    growth_interval: int = 2000
    backoff_factor: float = 0.5
    max_scale: float = 2.0**24
    enabled: bool = True

    def __post_init__(self) -> None:
        if self.scale <= 0:
            raise ValueError(f"Loss scale must be positive, got {self.scale}")
        if not 0.0 < self.backoff_factor < 1.0:
            raise ValueError(f"backoff_factor must be in (0, 1), got {self.backoff_factor}")
        self.growth_tracker = 0

    def scale_loss(self, loss: Tensor) -> Tensor:
        """Return ``loss`` multiplied by the scale, for the backward pass."""
        if not self.enabled:
            return loss
        return loss * self.scale

    def unscale(self, gradients: Sequence[Tensor | None]) -> float:
        """Divide gradients by the scale in place; returns their pre-scale norm."""
        if not self.enabled:
            return grad_norm([g for g in gradients if g is not None])
        inverse = 1.0 / self.scale
        for grad in gradients:
            if grad is None:
                continue
            values = grad.numpy()
            values[...] = (values * inverse).astype(grad.dtype.np_dtype)
        return grad_norm([g for g in gradients if g is not None])

    def step_update(self, found_inf: bool) -> bool:
        """Record whether a step overflowed; returns whether it should be skipped.

        An overflow halves the scale and skips the update. A run of clean steps
        doubles it again, so the scale tracks the largest value that stays in
        range rather than drifting to one extreme.
        """
        if not self.enabled:
            return False
        if found_inf:
            self.scale = max(1.0, self.scale * self.backoff_factor)
            self.growth_tracker = 0
            return True

        self.growth_tracker += 1
        if self.growth_tracker >= self.growth_interval and self.scale < self.max_scale:
            self.scale *= 2.0
            self.growth_tracker = 0
        return False

    def state_dict(self) -> dict[str, float | int | bool]:
        """Return the scaler state for checkpointing."""
        return {
            "scale": self.scale,
            "growth_tracker": self.growth_tracker,
            "growth_interval": self.growth_interval,
            "backoff_factor": self.backoff_factor,
            "max_scale": self.max_scale,
            "enabled": self.enabled,
        }

    def load_state_dict(self, data: dict[str, Any]) -> None:
        """Restore scaler state."""
        self.scale = data.get("scale", self.scale)
        self.growth_tracker = data.get("growth_tracker", 0)
        self.growth_interval = data.get("growth_interval", self.growth_interval)
        self.backoff_factor = data.get("backoff_factor", self.backoff_factor)
        self.max_scale = data.get("max_scale", self.max_scale)
        self.enabled = data.get("enabled", self.enabled)

    def __repr__(self) -> str:
        return f"GradScaler(scale={self.scale:g}, growth_interval={self.growth_interval})"


def has_non_finite(gradients: Sequence[Tensor | None]) -> bool:
    """Return whether any gradient contains NaN or infinity."""
    for grad in gradients:
        if grad is None:
            continue
        if not bool(np.isfinite(grad.numpy()).all()):
            return True
    return False


def contains_dtype(dtype: Any) -> bool:
    """Return whether a type is one of the reduced-precision float types."""
    return resolve(dtype) in (FLOAT16, BFLOAT16)


@dataclass
class PrecisionConfig:
    """Which dtypes a forward and backward pass should use.

    Attributes:
        compute_dtype: the type activations are computed in.
        param_dtype: the type parameters are stored in.
        loss_scale: initial loss scale.
        autocast: whether reduced precision is used for operators that support it.
    """

    compute_dtype: DType = FLOAT16
    param_dtype: DType = FLOAT16
    loss_scale: float = 65536.0
    autocast: bool = True
    allow_bf16: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Return the configuration as a plain dictionary."""
        return {
            "compute_dtype": self.compute_dtype.name,
            "param_dtype": self.param_dtype.name,
            "loss_scale": self.loss_scale,
            "autocast": self.autocast,
            "allow_bf16": self.allow_bf16,
        }


class autocast:
    """Run a block in reduced precision.

    Reduced precision is applied to operations whose dynamic range tolerates
    it. Reductions and normalization statistics stay in float32: accumulating
    a long sequence in float16 loses the sum, and the loss is computed there.
    Usable as a context manager or a decorator.
    """

    #: Operators whose output is kept at the input precision.
    _preserved = frozenset(
        {
            "sum",
            "mean",
            "max",
            "min",
            "layer_norm",
            "rms_norm",
            "group_norm",
            "cross_entropy",
            "mse_loss",
            "l1_loss",
            "bce_loss",
            "huber_loss",
            "nll_loss",
            "log_softmax",
            "softmax",
            "matmul",
        }
    )

    def __init__(self, dtype: DType = FLOAT16, enabled: bool = True) -> None:
        self.dtype = resolve(dtype)
        self.enabled = enabled
        self._previous: Any = None

    def __enter__(self) -> "autocast":
        from astrovox.autograd import graph as graph_module

        self._previous = getattr(graph_module, "_AUTOCAST", None)
        setattr(graph_module, "_AUTOCAST", self.dtype if self.enabled else None)
        return self

    def __exit__(self, *exc_info: object) -> None:
        from astrovox.autograd import graph as graph_module

        setattr(graph_module, "_AUTOCAST", self._previous)

    def __call__(self, func: Any) -> Any:
        """Return ``func`` wrapped to run under autocast."""
        import functools

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with autocast(self.dtype, self.enabled):
                return func(*args, **kwargs)

        return wrapper


def active_autocast_dtype() -> DType | None:
    """Return the dtype autocast is currently imposing, if any."""
    from astrovox.autograd import graph as graph_module

    return getattr(graph_module, "_AUTOCAST", None)


def to_low_precision(t: Tensor, dtype: DType = FLOAT16) -> Tensor:
    """Return ``t`` cast to ``dtype``, with its shape preserved.

    Note on bfloat16: it is currently stored with the same two-byte width as
    float16 rather than with bfloat16's own exponent layout, so casting to it
    behaves as float16. A truncating conversion is the remaining work; until
    then float16 with loss scaling is the supported reduced-precision path,
    and bfloat16 is useful mainly for its wider dynamic range being
    emulated.
    """
    resolved = resolve(dtype)
    return Tensor.from_numpy(t.numpy().astype(resolved.np_dtype), resolved, t.device)


def from_low_precision(t: Tensor) -> Tensor:
    """Return ``t`` widened back to float32."""
    if t.dtype.name in ("float16", "bfloat16"):
        return Tensor.from_numpy(t.numpy().astype(np.float32), None, t.device)
    return t


class MixedPrecisionTrainer:
    """Runs training steps with loss scaling and overflow recovery.

    The scaler is the point of the class: a step whose gradients overflow is
    skipped rather than applied, and the scale is reduced so the next attempt
    is less likely to overflow. Without that, a half-precision run either
    diverges or silently stops updating.
    """

    def __init__(
        self,
        module: Any,
        optimizer: Any,
        config: PrecisionConfig | None = None,
    ) -> None:
        self.module = module
        self.optimizer = optimizer
        self.config = config or PrecisionConfig()
        self.scaler = GradScaler(scale=self.config.loss_scale, enabled=self.config.autocast)
        self.skipped_steps = 0
        self.total_steps = 0

    def step(self, loss_fn: Any) -> dict[str, Any]:
        """Run one step and return what happened.

        Returns a record with the loss, the gradient norm, whether the update
        was skipped for overflow, and the scale in force afterwards.
        """
        self.optimizer.zero_grad()
        loss = loss_fn()
        self.total_steps += 1

        scaled = self.scaler.scale_loss(loss)
        from astrovox.autograd import backward

        backward(scaled)

        gradients = [p.grad for p in self.module.parameters()]
        self.scaler.unscale(gradients)
        overflowed = has_non_finite(gradients)
        skip = self.scaler.step_update(overflowed)
        if skip:
            self.skipped_steps += 1
        else:
            if getattr(self.optimizer, "grad_clip", 0):
                self.optimizer.clip_grad_norm(self.optimizer.grad_clip)
            self.optimizer.step()

        return {
            "loss": float(loss.item()),
            "skipped": skip,
            "scale": self.scaler.scale,
            "grad_norm": 0.0 if skip else grad_norm([g for g in gradients if g is not None]),
        }

    def state_dict(self) -> dict[str, Any]:
        """Return the scaler state for checkpointing."""
        return {
            "scaler": self.scaler.state_dict(),
            "skipped_steps": self.skipped_steps,
            "total_steps": self.total_steps,
        }

    def load_state_dict(self, data: dict[str, Any]) -> None:
        """Restore the scaler state."""
        if "scaler" in data:
            self.scaler.load_state_dict(data["scaler"])
        self.skipped_steps = data.get("skipped_steps", 0)
        self.total_steps = data.get("total_steps", 0)
