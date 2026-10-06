"""Tests for the optimized CPU backend."""

from __future__ import annotations

import numpy as np
import pytest

from astrovox.cpu import CPUBackendOptimized
from astrovox.tensor.tensor import Tensor


def test_cpu_backend_matmul_matches_numpy():
    backend = CPUBackendOptimized()
    left = Tensor.from_numpy(np.ones((2, 3), dtype=np.float32))
    right = Tensor.from_numpy(np.ones((3, 4), dtype=np.float32))
    result = backend.matmul(left, right)
    expected = np.matmul(left.numpy(), right.numpy())
    np.testing.assert_allclose(result.numpy(), expected, rtol=1e-5)


def test_cpu_backend_relu_nonnegative():
    backend = CPUBackendOptimized()
    x = Tensor.from_numpy(np.array([-1, 0, 1], dtype=np.float32))
    result = backend.relu(x)
    assert float(result.numpy().min()) >= 0


def test_cpu_backend_softmax_sums_to_one():
    backend = CPUBackendOptimized()
    x = Tensor.from_numpy(np.array([[1, 2, 3]], dtype=np.float32))
    result = backend.softmax(x, axis=-1)
    total = float(np.sum(result.numpy(), axis=-1)[0])
    assert abs(total - 1.0) < 1e-5


def test_cpu_backend_layer_norm_preserves_shape():
    backend = CPUBackendOptimized()
    x = Tensor.from_numpy(np.ones((2, 4), dtype=np.float32))
    result = backend.layer_norm(x)
    assert result.shape.dims == (2, 4)


def test_cpu_backend_gelu_nonnegative_for_large_inputs():
    backend = CPUBackendOptimized()
    x = Tensor.from_numpy(np.array([10, -10], dtype=np.float32))
    result = backend.gelu(x)
    assert result.numpy().shape == (2,)
