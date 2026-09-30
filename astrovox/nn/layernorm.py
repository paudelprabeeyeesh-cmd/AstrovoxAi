"""Layer normalization."""

from __future__ import annotations

from typing import Sequence

import numpy as np

from astrovox.nn.module import Module, init_ones, init_zeros, parameter
from astrovox.ops.normalization import layer_norm
from astrovox.tensor.tensor import Tensor


def _as_shape(normalized_shape: Sequence[int] | int) -> tuple[int, ...]:
    """Accept either a single width or a full shape."""
    if isinstance(normalized_shape, int):
        return (normalized_shape,)
    return tuple(normalized_shape)


class LayerNorm(Module):
    """Layer normalization over the trailing ``normalized_shape`` dimensions.

    Each sample is normalized independently using its own mean and variance,
    so the result does not depend on batch composition. That property is why
    transformers use it instead of batch normalization.

    Args:
        normalized_shape: the trailing dimensions to normalize together.
        eps: floor added to the variance for numerical stability.
        bias: whether to learn a per-channel shift.
    """

    def __init__(self, normalized_shape: Sequence[int] | int, eps: float = 1e-5, bias: bool = True) -> None:
        super().__init__()
        self.normalized_shape = _as_shape(normalized_shape)
        self.eps = eps

        features = int(np.prod(self.normalized_shape))
        self.weight = parameter(np.ones(features, dtype=np.float32), "weight")
        init_ones(self.weight)
        if bias:
            self.bias = parameter(np.zeros(features, dtype=np.float32), "bias")
            init_zeros(self.bias)
        else:
            self.register_parameter("bias", None)

    def forward(self, x: Tensor) -> Tensor:
        """Normalize ``x`` over its trailing dimensions."""
        if tuple(x.shape.dims[len(x.shape.dims) - len(self.normalized_shape) :]) != self.normalized_shape:
            raise ValueError(
                f"LayerNorm expects trailing dimensions {self.normalized_shape}, got {tuple(x.shape.dims)}"
            )
        return layer_norm(
            x,
            self.normalized_shape,
            weight=self.weight,
            bias=self.bias if self.bias is not None else None,
            eps=self.eps,
        )

    def extra_repr(self) -> str:
        """Return the configuration for ``__repr__``."""
        return f"{self.normalized_shape}, eps={self.eps}"

    def __repr__(self) -> str:
        return f"LayerNorm({self.extra_repr()})"
