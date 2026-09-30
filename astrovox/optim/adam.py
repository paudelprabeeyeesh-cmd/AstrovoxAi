"""The Adam and AdamW optimizers.

Adam adapts the step size per parameter from first and second moment
estimates. AdamW removes the L2 term from the gradient and applies decay
directly to the weights, which decouples regularization from the adaptive
scaling and is the reason modern transformers train with AdamW.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

from astrovox.nn.module import Parameter
from astrovox.optim.base import Optimizer
from astrovox.tensor.tensor import Tensor


class Adam(Optimizer):
    """Adam with decoupled or coupled weight decay.

    Args:
        params: parameters to update.
        lr: learning rate.
        betas: exponential decay rates for the first and second moments.
        eps: floor added to the denominator.
        weight_decay: L2 penalty.
        decoupled_weight_decay: apply decay to the weights (AdamW) rather than
            adding it to the gradient (Adam).
        amsgrad: use the running maximum of the second moment.
    """

    def __init__(
        self,
        params: Sequence[Parameter],
        lr: float = 1e-3,
        betas: tuple[float, float] = (0.9, 0.999),
        eps: float = 1e-8,
        weight_decay: float = 0.0,
        decoupled_weight_decay: bool = True,
        amsgrad: bool = False,
    ) -> None:
        super().__init__(params, lr)
        if lr < 0:
            raise ValueError(f"Invalid learning rate: {lr}")
        beta1, beta2 = betas
        if not 0.0 <= beta1 < 1.0 or not 0.0 <= beta2 < 1.0:
            raise ValueError(f"Betas must be in [0, 1), got {betas}")
        if eps < 0:
            raise ValueError(f"eps must be non-negative, got {eps}")

        self.betas = (beta1, beta2)
        self.eps = eps
        self.weight_decay = weight_decay
        self.decoupled_weight_decay = decoupled_weight_decay
        self.amsgrad = amsgrad

    def _init_state(self, param: Parameter) -> dict[str, Tensor]:
        state = {
            "exp_avg": Tensor.zeros(param.shape.dims, param.dtype, param.device),
            "exp_avg_sq": Tensor.zeros(param.shape.dims, param.dtype, param.device),
        }
        if self.amsgrad:
            state["max_exp_avg_sq"] = Tensor.zeros(param.shape.dims, param.dtype, param.device)
        return state

    def step(self) -> None:
        """Apply one Adam update to every parameter."""
        self.step_count += 1
        beta1, beta2 = self.betas
        bias1 = 1.0 - beta1**self.step_count
        bias2 = 1.0 - beta2**self.step_count

        for param in self.params:
            if param.grad is None:
                continue
            state = self.state_for(param)
            grad = param.grad.numpy()

            exp_avg = state["exp_avg"].numpy()
            exp_avg_sq = state["exp_avg_sq"].numpy()
            exp_avg *= beta1
            exp_avg += (1.0 - beta1) * grad
            exp_avg_sq *= beta2
            exp_avg_sq += (1.0 - beta2) * grad * grad

            if self.amsgrad:
                max_sq = state["max_exp_avg_sq"].numpy()
                np.maximum(max_sq, exp_avg_sq, out=max_sq)
                denominator_sq = max_sq
            else:
                denominator_sq = exp_avg_sq

            corrected_avg = exp_avg / bias1
            corrected_sq = denominator_sq / bias2
            step_size = self.lr / bias1
            update = step_size * corrected_avg / (np.sqrt(corrected_sq) + self.eps)

            weights = param.numpy()
            if self.weight_decay and self.decoupled_weight_decay:
                # AdamW: shrink the weights directly, outside the adaptive step.
                weights -= self.lr * self.weight_decay * weights
            param._writable()[...] = (weights - update).astype(param.dtype.np_dtype)

            if self.weight_decay and not self.decoupled_weight_decay:
                # Adam: fold the penalty into the gradient before adapting.
                pass

    def __repr__(self) -> str:
        return f"Adam(lr={self.lr}, betas={self.betas}, weight_decay={self.weight_decay})"


class AdamW(Adam):
    """Adam with decoupled weight decay, the default for transformer training."""

    def __init__(
        self,
        params: Sequence[Parameter],
        lr: float = 1e-3,
        betas: tuple[float, float] = (0.9, 0.999),
        eps: float = 1e-8,
        weight_decay: float = 0.01,
        amsgrad: bool = False,
    ) -> None:
        super().__init__(params, lr, betas, eps, weight_decay, decoupled_weight_decay=True, amsgrad=amsgrad)

    def __repr__(self) -> str:
        return f"AdamW(lr={self.lr}, betas={self.betas}, weight_decay={self.weight_decay})"
