"""Tests for CPU backend - expanded coverage."""

from __future__ import annotations

import numpy as np
import pytest

from astrovox.cpu import CPUBackendOptimized
from astrovox.tensor.tensor import Tensor


def test_cpu_backend_add_broadcast():
    backend = CPUBackendOptimized()
    left = Tensor.from_numpy(np.ones((1, 3), dtype=np.float32))
    right = Tensor.from_numpy(np.ones((3,), dtype=np.float32))
    result = backend.add(left, right)
    assert result.shape.dims == (1, 3)


def test_cpu_backend_matmul_batched():
    backend = CPUBackendOptimized()
    left = Tensor.from_numpy(np.ones((2, 3, 4), dtype=np.float32))
    right = Tensor.from_numpy(np.ones((2, 4, 5), dtype=np.float32))
    result = backend.matmul(left, right)
    assert result.shape.dims == (2, 3, 5)


def test_cpu_backend_gelu_shape():
    backend = CPUBackendOptimized()
    x = Tensor.from_numpy(np.ones((2, 4), dtype=np.float32))
    result = backend.gelu(x)
    assert result.shape.dims == (2, 4)


def test_cpu_backend_broadcast_to():
    backend = CPUBackendOptimized()
    x = Tensor.from_numpy(np.ones((3,), dtype=np.float32))
    result = backend.broadcast_to(x, (2, 3))
    assert result.shape.dims == (2, 3)


def test_cpu_backend_contiguous_returns_same_shape():
    backend = CPUBackendOptimized()
    x = Tensor.from_numpy(np.ones((2, 3), dtype=np.float32))
    result = backend.contiguous(x)
    assert result.shape.dims == (2, 3)
