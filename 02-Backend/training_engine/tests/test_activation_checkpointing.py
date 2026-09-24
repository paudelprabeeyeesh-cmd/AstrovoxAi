import numpy as np
import pytest
from training_engine.activation_checkpointing import ActivationCheckpoint


def _relu(x):
    return np.maximum(x, 0.0)


def test_forward_saves_input():
    cp = ActivationCheckpoint(_relu)
    x = np.array([-1.0, 0.0, 1.0])
    out = cp.forward(x)
    assert np.allclose(out, np.array([0.0, 0.0, 1.0]))
    assert np.allclose(cp._saved_input, x)


def test_backward_recomputes():
    cp = ActivationCheckpoint(_relu)
    x = np.array([-1.0, 0.0, 1.0])
    cp.forward(x)
    grad = np.array([1.0, 1.0, 1.0])
    out = cp.backward(grad)
    expected = np.array([0.0, 0.0, 1.0])
    assert np.allclose(out, expected)
