"""RMS normalization.

RMSNorm drops the mean subtraction and the bias, which makes it roughly twice
as cheap as LayerNorm and empirically equivalent for most transformer
configurations. Modern large language models use it almost exclusively.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

from astrovox.nn.module import Module, init_ones, parameter
from astrovox.ops.normalization import rms_norm
from astrovox.tensor.tensor import Tensor


class RMSNorm(Module):
    """Root-mean-square normalization over trailing dimensions.

    Args:
        normalized_shape: the trailing dimensions to normalize together.
        eps: floor added to the mean square for numerical stability.
    """

    def __init__(self, normalized_shape: Sequence[int] | int, eps: float = 1e-6) -> None:
        super().__init__()
        self.normalized_shape = (normalized_shape,) if isinstance(normalized_shape, int) else tuple(normalized_shape)
        self.eps = eps
        features = int(np.prod(self.normalized_shape))
        self.weight = parameter(np.ones(features, dtype=np.float32), "weight")
        init_ones(self.weight)

    def forward(self, x: Tensor) -> Tensor:
        """RMS-normalize ``x`` over its trailing dimensions."""
        trailing = tuple(x.shape.dims[len(x.shape.dims) - len(self.normalized_shape) :])
        if trailing != self.normalized_shape:
            raise ValueError(
                f"RMSNorm expects trailing dimensions {self.normalized_shape}, got {tuple(x.shape.dims)}"
            )
        return rms_norm(x, self.normalized_shape, weight=self.weight, eps=self.eps)

    def extra_repr(self) -> str:
        """Return the configuration for ``__repr__``."""
        return f"{self.normalized_shape}, eps={self.eps}"

    def __repr__(self) -> str:
        return f"RMSNorm({self.extra_repr()})"
