"""The Lion optimizer.

Lion ("EvoLved Sign Momentum") keeps only a single momentum buffer and derives
the update from the sign of the gradient, which costs about 75% less memory
than Adam and needs roughly 3 to 4 times fewer optimizer steps. It reaches a
given loss faster but plateaus at a worse value, so it suits pretraining on a
compute budget rather than squeezing out the last drop of quality.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

from astrovox.nn.module import Parameter
from astrovox.optim.base import Optimizer
from astrovox.tensor.tensor import Tensor


class Lion(Optimizer):
    """Sign-based optimizer with a single momentum buffer.

    Args:
        params: parameters to update.
        lr: learning rate; Lion typically uses 3 to 10 times less than AdamW.
        betas: the two decay rates interleaving the sign updates.
        weight_decay: decoupled L2 penalty.
    """

    def __init__(
        self,
        params: Sequence[Parameter],
        lr: float = 1e-4,
        betas: tuple[float, float] = (0.9, 0.99),
        weight_decay: float = 0.0,
    ) -> None:
        super().__init__(params, lr)
        beta1, beta2 = betas
        if not 0.0 <= beta1 < 1.0 or not 0.0 <= beta2 < 1.0:
            raise ValueError(f"Betas must be in [0, 1), got {betas}")
        self.betas = betas
        self.weight_decay = weight_decay

    def _init_state(self, param: Parameter) -> dict[str, Tensor]:
        return {"momentum": Tensor.zeros(param.shape.dims, param.dtype, param.device)}

    def step(self) -> None:
        """Apply one Lion update to every parameter."""
        self.step_count += 1
        beta1, beta2 = self.betas

        for param in self.params:
            if param.grad is None:
                continue
            state = self.state_for(param)
            momentum = state["momentum"]
            grad = param.grad.numpy()

            # Update in the direction of the current gradient's sign, then let
            # the momentum buffer interpolate toward it.
            update = np.sign(momentum.numpy() * beta1 + grad * (1.0 - beta1))
            weights = param.numpy()
            if self.weight_decay:
                weights -= self.lr * self.weight_decay * weights
            weights -= self.lr * update
            param._writable()[...] = weights.astype(param.dtype.np_dtype)

            # Store the current gradient for the next step to interpolate with.
            momentum.numpy()[...] = (beta2 * momentum.numpy() + grad * (1.0 - beta2)).astype(momentum.dtype.np_dtype)

    def __repr__(self) -> str:
        return f"Lion(lr={self.lr}, betas={self.betas}, weight_decay={self.weight_decay})"
