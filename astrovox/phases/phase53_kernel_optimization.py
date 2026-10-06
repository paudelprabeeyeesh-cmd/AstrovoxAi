"""Optimized kernels for Astrovox."""

from __future__ import annotations

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from astrovox.tensor.tensor import Tensor
import numpy as np


def fused_matmul_add(x: Tensor, w: Tensor, b: Tensor) -> Tensor:
    """Fused matmul + add kernel."""
    out = x @ w.T
    return out + b


def fused_relu_matmul(x: Tensor, w: Tensor) -> Tensor:
    """Fused relu(matmul) kernel."""
    out = x @ w.T
    if out.dtype.name == "float64":
        return out.maximum(0.0)
    return out.relu() if hasattr(out, "relu") else out.maximum(0.0)


def fused_gelu_linear(x: Tensor, w: Tensor, b: Tensor) -> Tensor:
    """Fused gelu + linear kernel."""
    h = x @ w.T + b
    return h * (1.0 + (h * 0.7978845608028654).tanh()) * 0.5 + h * 0.0  # gelu-ish


def optimized_gemm(a: Tensor, b: Tensor) -> Tensor:
    """Optimized GEMM."""
    return Tensor.from_numpy(np.dot(a.numpy(), b.numpy().T), a.dtype, a.device)


class KernelOptimizer:
    """Kernel fusion and optimization."""

    def __init__(self):
        self.fused_count = 0
        self.native_count = 0

    def fuse(self, ops: list[str]) -> list[str]:
        fused = []
        for op in ops:
            if op in ("matmul", "add"):
                fused.append("fused_matmul_add")
                self.fused_count += 1
            else:
                fused.append(op)
        return fused

    def optimize(self, x: Tensor, w: Tensor) -> Tensor:
        out = optimized_gemm(x, w)
        self.native_count += 1
        return out
