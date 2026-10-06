"""Tests for the execution backend registry."""

from __future__ import annotations

import numpy as np
import pytest

from astrovox.backends import BackendRegistry, CPUBackend


def test_cpu_backend_is_registered_by_default():
    backend = BackendRegistry.default()
    assert backend is not None
    assert backend.info.name == "cpu"


def test_cpu_backend_matmul_produces_correct_shape():
    backend = CPUBackend()
    left = np.ones((2, 3), dtype=np.float32)
    right = np.ones((3, 4), dtype=np.float32)
    result = backend.matmul(left, right)
    assert result.shape == (2, 4)


def test_cpu_backend_add_matches_numpy():
    backend = CPUBackend()
    left = np.ones((2, 3), dtype=np.float32)
    right = np.ones((2, 3), dtype=np.float32) * 2
    result = backend.add(left, right)
    expected = np.add(left, right)
    np.testing.assert_allclose(result, expected, rtol=1e-5)


def test_cpu_backend_relu_nonnegative():
    backend = CPUBackend()
    x = np.array([-1, 0, 1], dtype=np.float32)
    result = backend.relu(x)
    assert float(result.min()) >= 0


def test_backend_registry_get_unknown_raises():
    with pytest.raises(KeyError):
        BackendRegistry.get("unknown_backend")
