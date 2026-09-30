"""Stochastic gradient descent, with momentum and weight decay.

SGD remains the best choice for well-conditioned problems and is the optimizer
of record for many theoretical results, so it is included in full rather than
as an afterthought.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

from astrovox.nn.module import Parameter
from astrovox.optim.base import Optimizer
from astrovox.tensor.tensor import Tensor


class SGD(Optimizer):
    """Plain SGD, optionally with momentum and L2 weight decay.

    Args:
        params: parameters to update.
        lr: learning rate.
        momentum: velocity coefficient; 0 disables momentum.
        weight_decay: L2 penalty added to the gradient.
        dampening: damping applied to the momentum buffer.
        nesterov: whether to use the Nesterov variant.
    """

    def __init__(
        self,
        params: Sequence[Parameter],
        lr: float = 1e-3,
        momentum: float = 0.0,
        weight_decay: float = 0.0,
        dampening: float = 0.0,
        nesterov: bool = False,
    ) -> None:
        super().__init__(params, lr)
        if lr < 0:
            raise ValueError(f"Invalid learning rate: {lr}")
        if not 0.0 <= momentum < 1.0:
            raise ValueError(f"Momentum must be in [0, 1), got {momentum}")
        if nesterov and (momentum <= 0 or dampening != 0):
            raise ValueError("Nesterov momentum requires momentum > 0 and dampening = 0")
        self.momentum = momentum
        self.weight_decay = weight_decay
        self.dampening = dampening
        self.nesterov = nesterov

    def _init_state(self, param: Parameter) -> dict[str, Tensor]:
        return {"velocity": Tensor.zeros(param.shape.dims, param.dtype, param.device)} if self.momentum else {}

    def step(self) -> None:
        """Apply one SGD update to every parameter."""
        self.step_count += 1
        for param in self.params:
            if param.grad is None:
                continue
            grad = param.grad
            if self.weight_decay:
                grad = grad + param * self.weight_decay

            if not self.momentum:
                param._writable()[...] = (param.numpy() - self.lr * grad.numpy()).astype(param.dtype.np_dtype)
                continue

            state = self.state_for(param)
            velocity = state["velocity"]
            buffer = grad.numpy() + self.dampening * velocity.numpy()
            velocity.numpy()[...] = (self.momentum * buffer).astype(velocity.dtype.np_dtype)

            direction = (grad.numpy() + self.momentum * buffer) if self.nesterov else buffer
            param._writable()[...] = (param.numpy() - self.lr * direction).astype(param.dtype.np_dtype)

    def __repr__(self) -> str:
        return f"SGD(lr={self.lr}, momentum={self.momentum}, weight_decay={self.weight_decay})"
