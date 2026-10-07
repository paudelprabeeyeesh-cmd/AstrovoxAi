"""Tests for backends - expanded coverage."""

from __future__ import annotations

import numpy as np
import pytest

from astrovox.backends import BackendRegistry, CPUBackend


def test_backend_registry_default_returns_cpu():
    backend = BackendRegistry.default()
    assert backend.info.name == "cpu"


def test_cpu_backend_softmax_matches_numpy():
    backend = CPUBackend()
    x = np.array([[1, 2, 3]], dtype=np.float32)
    result = backend.softmax(x, dim=-1)
    expected = np.exp(x - np.max(x, axis=-1, keepdims=True))
    expected = expected / expected.sum(axis=-1, keepdims=True)
    np.testing.assert_allclose(result, expected, rtol=1e-5)


def test_cpu_backend_relu_negative_inputs():
    backend = CPUBackend()
    x = np.array([[-1, -2, 3]], dtype=np.float32)
    result = backend.relu(x)
    assert float(result.min()) >= 0
    assert float(result.max()) == 3
