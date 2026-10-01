"""Base class and shared state for optimizers."""

from __future__ import annotations

from typing import Any, Iterator, Sequence

import numpy as np

from astrovox.autograd.engine import clip_grad_norm, grad_norm
from astrovox.nn.module import Module, Parameter
from astrovox.tensor.tensor import Tensor


class Optimizer:
    """Base class for parameter update rules.

    Subclasses implement :meth:`step`. Gradient accumulation is handled here:
    an optimizer only steps when :meth:`step` is called, so running
    ``loss.backward()`` several times before a single ``step()`` naturally
    sums the gradients. ``zero_grad`` clears them between updates.
    """

    def __init__(self, params: Sequence[Parameter], lr: float = 1e-3) -> None:
        self.params = [p for p in params if p is not None and p.requires_grad]
        if not self.params:
            raise ValueError("Optimizer received no trainable parameters")
        self.lr = lr
        self.state: dict[int, dict[str, Tensor]] = {}
        self.step_count = 0
        # State is keyed by position in ``self.params``, not by id(param).
        # An id is only meaningful inside one process, so keying on it would
        # make a checkpoint unusable after being reloaded: the restored entry
        # would never be found and the optimizer would silently start fresh.
        self._slots: dict[int, int] = {id(p): i for i, p in enumerate(self.params)}

    def state_for(self, param: Parameter) -> dict[str, Tensor]:
        """Return the per-parameter state, creating it on first use."""
        key = self._slot_of(param)
        if key not in self.state:
            self.state[key] = self._init_state(param)
        return self.state[key]

    def _slot_of(self, param: Parameter) -> int:
        """Return the stable index of ``param`` within this optimizer."""
        key = self._slots.get(id(param))
        if key is not None:
            return key
        # A parameter added after construction gets a fresh slot.
        key = len(self.params)
        self._slots[id(param)] = key
        self.params.append(param)
        return key

    def _init_state(self, param: Parameter) -> dict[str, Tensor]:
        """Create the per-parameter state; optimized ones override this."""
        return {}

    def step(self) -> None:
        """Apply one update to every parameter. Subclasses must implement this."""
        raise NotImplementedError(f"{type(self).__name__} must implement step()")

    def zero_grad(self, set_to_none: bool = True) -> None:
        """Clear accumulated gradients."""
        for param in self.params:
            if set_to_none:
                param._grad = None
            elif param._grad is not None:
                param._grad = param._grad * 0.0

    def clip_grad_norm(self, max_norm: float) -> float:
        """Clip the total gradient norm, returning the pre-clip value."""
        return clip_grad_norm([p.grad for p in self.params if p.grad is not None], max_norm)

    def grad_norm(self) -> float:
        """Return the current total gradient L2 norm."""
        return grad_norm([p.grad for p in self.params if p.grad is not None])

    def add_param_group(self, params: Sequence[Parameter], lr: float | None = None) -> None:
        """Add parameters to this optimizer, optionally at a different rate."""
        for param in params:
            if not param.requires_grad or id(param) in self._slots:
                continue
            self._slots[id(param)] = len(self.params)
            self.params.append(param)
        if lr is not None:
            self.lr = lr

    def state_dict(self) -> dict[str, Any]:
        """Return optimizer state for checkpointing."""
        return {
            "type": type(self).__name__,
            "lr": self.lr,
            "step_count": self.step_count,
            "state": {
                str(key): {k: v.numpy().copy() for k, v in entry.items()} for key, entry in self.state.items()
            },
        }

    def load_state_dict(self, data: dict[str, Any]) -> None:
        """Restore optimizer state written by :meth:`state_dict`."""
        self.lr = data.get("lr", self.lr)
        self.step_count = data.get("step_count", 0)
        self.state = {
            int(key): {k: Tensor.from_numpy(np.asarray(v)) for k, v in entry.items()}
            for key, entry in data.get("state", {}).items()
        }

    def __repr__(self) -> str:
        return f"{type(self).__name__}(lr={self.lr}, params={len(self.params)}, steps={self.step_count})"
