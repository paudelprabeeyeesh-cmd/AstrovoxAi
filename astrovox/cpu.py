"""CPU execution backend with optimized tensor operations.

Provides optimized implementations of common operations using NumPy under
the hood, with explicit memory layout handling and cache-friendly access
patterns.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from astrovox.tensor.dtype import DEFAULT, DType
from astrovox.tensor.tensor import Tensor


class CPUBackendOptimized:
    """Optimized CPU backend for tensor operations."""

    @staticmethod
    def matmul(left: Tensor, right: Tensor) -> Tensor:
        left_array = left.numpy()
        right_array = right.numpy()
        if left_array.ndim == 1:
            left_array = left_array.reshape(1, -1)
        if right_array.ndim == 1:
            right_array = right_array.reshape(-1, 1)
        out = np.matmul(left_array, right_array)
        return Tensor.from_numpy(out.astype(left.dtype.np_dtype), left.dtype, left.device)

    @staticmethod
    def add(left: Tensor, right: Tensor) -> Tensor:
        out = np.add(left.numpy(), right.numpy())
        return Tensor.from_numpy(out.astype(left.dtype.np_dtype), left.dtype, left.device)

    @staticmethod
    def relu(x: Tensor) -> Tensor:
        out = np.maximum(x.numpy(), 0)
        return Tensor.from_numpy(out.astype(x.dtype.np_dtype), x.dtype, x.device)

    @staticmethod
    def softmax(x: Tensor, axis: int = -1) -> Tensor:
        array = x.numpy().astype(np.float64)
        max_val = np.max(array, axis=axis, keepdims=True)
        exp = np.exp(array - max_val)
        out = exp / np.sum(exp, axis=axis, keepdims=True)
        return Tensor.from_numpy(out.astype(x.dtype.np_dtype), x.dtype, x.device)

    @staticmethod
    def layer_norm(x: Tensor, eps: float = 1e-5) -> Tensor:
        array = x.numpy().astype(np.float64)
        mean = np.mean(array, axis=-1, keepdims=True)
        variance = np.var(array, axis=-1, keepdims=True)
        out = (array - mean) / np.sqrt(variance + eps)
        return Tensor.from_numpy(out.astype(x.dtype.np_dtype), x.dtype, x.device)

    @staticmethod
    def gelu(x: Tensor) -> Tensor:
        array = x.numpy().astype(np.float64)
        out = 0.5 * array * (1 + np.tanh(np.sqrt(2 / np.pi) * (array + 0.044715 * np.power(array, 3))))
        return Tensor.from_numpy(out.astype(x.dtype.np_dtype), x.dtype, x.device)

    @staticmethod
    def broadcast_to(x: Tensor, shape: tuple) -> Tensor:
        out = np.broadcast_to(x.numpy(), shape).copy()
        return Tensor.from_numpy(out.astype(x.dtype.np_dtype), x.dtype, x.device)

    @staticmethod
    def contiguous(x: Tensor) -> Tensor:
        out = np.ascontiguousarray(x.numpy())
        return Tensor.from_numpy(out.astype(x.dtype.np_dtype), x.dtype, x.device)
