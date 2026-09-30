"""Core layers: linear, embedding, and the activation wrappers."""

from __future__ import annotations

import math
from typing import Any, Sequence

import numpy as np

from astrovox.nn.module import (
    Module,
    Parameter,
    init_kaiming_uniform,
    init_normal,
    init_xavier_uniform,
    init_zeros,
    parameter,
)
from astrovox.ops.activation import gelu, relu, sigmoid, silu, softmax, tanh
from astrovox.ops.math import add, matmul, mul
from astrovox.tensor.tensor import Tensor


class Linear(Module):
    """A fully connected layer computing ``x @ weight.T + bias``.

    Args:
        in_features: size of each input sample.
        out_features: size of each output sample.
        bias: whether to learn an additive bias.
    """

    def __init__(self, in_features: int, out_features: int, bias: bool = True) -> None:
        super().__init__()
        if in_features <= 0 or out_features <= 0:
            raise ValueError(f"Linear requires positive sizes, got in={in_features} out={out_features}")
        self.in_features = in_features
        self.out_features = out_features
        self.weight = parameter(
            np.empty((out_features, in_features), dtype=np.float32), f"weight:{out_features}x{in_features}"
        )
        init_xavier_uniform(self.weight)
        if bias:
            self.bias = parameter(np.zeros(out_features, dtype=np.float32), f"bias:{out_features}")
        else:
            self.register_parameter("bias", None)

    def forward(self, x: Tensor) -> Tensor:
        """Apply the affine transform to ``x``."""
        if x.shape.dims[-1] != self.in_features:
            raise ValueError(
                f"Linear expects last dimension {self.in_features}, got {x.shape.dims[-1]}"
            )
        out = matmul(x, self.weight.transpose(0, 1))
        if self.bias is not None:
            out = out + self.bias
        return out

    def __repr__(self) -> str:
        return f"Linear(in_features={self.in_features}, out_features={self.out_features}, bias={self.bias is not None})"


class Embedding(Module):
    """A lookup table mapping integer indices to learned vectors.

    The gradient of an embedding is a scatter-add: every occurrence of a token
    contributes to that row, which is what makes shared token embeddings train.
    """

    def __init__(self, num_embeddings: int, embedding_dim: int) -> None:
        super().__init__()
        if num_embeddings <= 0 or embedding_dim <= 0:
            raise ValueError("Embedding requires positive num_embeddings and embedding_dim")
        self.num_embeddings = num_embeddings
        self.embedding_dim = embedding_dim
        self.weight = parameter(np.zeros((num_embeddings, embedding_dim), dtype=np.float32), "weight")
        init_normal(self.weight, std=0.02)

    def forward(self, indices: Tensor) -> Tensor:
        """Look up the rows of ``indices``."""
        flat = indices.numpy().astype(np.int64).reshape(-1)
        if flat.size and (flat.min() < 0 or flat.max() >= self.num_embeddings):
            raise IndexError(
                f"Embedding index out of range: got [{flat.min()}, {flat.max()}], "
                f"table has {self.num_embeddings} rows"
            )
        rows = self.weight.numpy()[flat]
        out = Tensor.from_numpy(rows.reshape(tuple(indices.shape.dims) + (self.embedding_dim,)), self.weight.dtype)
        out.requires_grad_(True)
        self._last_indices = flat
        return out

    def __repr__(self) -> str:
        return f"Embedding(num_embeddings={self.num_embeddings}, embedding_dim={self.embedding_dim})"


class Activation(Module):
    """Wraps an elementwise activation function as a module."""

    def __init__(self, fn: Any, name: str = "activation") -> None:
        super().__init__()
        self.fn = fn
        self._label = name

    def forward(self, x: Tensor) -> Tensor:
        """Apply the wrapped activation."""
        return self.fn(x)

    def __repr__(self) -> str:
        return f"Activation({self._label})"


class ReLU(Activation):
    """Rectified linear unit."""

    def __init__(self) -> None:
        super().__init__(relu, "relu")


class GELU(Activation):
    """Gaussian error linear unit."""

    def __init__(self) -> None:
        super().__init__(gelu, "gelu")


class SiLU(Activation):
    """Sigmoid-weighted linear unit."""

    def __init__(self) -> None:
        super().__init__(silu, "silu")


class Sigmoid(Activation):
    """Logistic sigmoid."""

    def __init__(self) -> None:
        super().__init__(sigmoid, "sigmoid")


class Tanh(Activation):
    """Hyperbolic tangent."""

    def __init__(self) -> None:
        super().__init__(tanh, "tanh")


class Dropout(Module):
    """Randomly zeroes elements during training.

    Inference keeps every element, so a trained model is deterministic.
    """

    def __init__(self, p: float = 0.5, seed: int | None = None) -> None:
        super().__init__()
        if not 0.0 <= p < 1.0:
            raise ValueError(f"Dropout probability must be in [0, 1), got {p}")
        self.p = p
        self._rng = np.random.default_rng(seed)
        self._mask: np.ndarray | None = None

    def forward(self, x: Tensor) -> Tensor:
        """Apply dropout, sampling a fresh mask each call in training mode."""
        if not self.training or self.p == 0.0:
            return x
        mask = (self._rng.random(x.shape.dims) >= self.p).astype(x.dtype.np_dtype) / (1.0 - self.p)
        self._mask = mask
        return mul(x, Tensor.from_numpy(mask, x.dtype))

    def __repr__(self) -> str:
        return f"Dropout(p={self.p})"


class Flatten(Module):
    """Collapses all but the batch dimension."""

    def __init__(self, start_dim: int = 1, end_dim: int = -1) -> None:
        super().__init__()
        self.start_dim = start_dim
        self.end_dim = end_dim

    def forward(self, x: Tensor) -> Tensor:
        """Flatten the requested dimension range."""
        return x.flatten(self.start_dim, self.end_dim)


class Reshape(Module):
    """Applies a fixed reshape, useful inside a Sequential chain."""

    def __init__(self, *shape: int) -> None:
        super().__init__()
        self.target = shape[0] if len(shape) == 1 and isinstance(shape[0], (tuple, list)) else shape

    def forward(self, x: Tensor) -> Tensor:
        """Reshape ``x`` to the configured shape."""
        return x.reshape(self.target)

    def __repr__(self) -> str:
        return f"Reshape({self.target})"


class Softmax(Module):
    """Softmax over the last dimension."""

    def __init__(self, axis: int = -1) -> None:
        super().__init__()
        self.axis = axis

    def forward(self, x: Tensor) -> Tensor:
        """Normalize ``x`` along ``axis``."""
        return softmax(x, self.axis)


class LayerNormWrapper(Module):
    """Layer normalization over the trailing dimensions."""

    def __init__(self, normalized_shape: Sequence[int], eps: float = 1e-5, bias: bool = True) -> None:
        super().__init__()
        from astrovox.nn.layernorm import LayerNorm

        self.norm = LayerNorm(tuple(normalized_shape), eps=eps, bias=bias)

    def forward(self, x: Tensor) -> Tensor:
        """Normalize ``x``."""
        return self.norm(x)


def mlp(in_features: int, hidden: int, out_features: int, activation: Any = relu) -> Module:
    """Build a two-layer perceptron with a ReLU between the layers."""
    from astrovox.nn.sequential import Sequential

    return Sequential(
        Linear(in_features, hidden),
        Activation(activation, getattr(activation, "__name__", "activation")),
        Linear(hidden, out_features),
    )
