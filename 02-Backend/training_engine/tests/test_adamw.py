import numpy as np
import pytest
from training_engine.adamw import AdamW


def test_adamw_step_changes_params():
    np.random.seed(0)
    p = [np.random.randn(4, 4).astype(np.float32)]
    opt = AdamW(p, lr=1e-2)
    g = [np.random.randn(4, 4).astype(np.float32)]
    new_params = opt.step(g)
    assert not np.allclose(new_params[0], p[0])


def test_adamw_bias_correction():
    np.random.seed(1)
    p = [np.zeros((4, 4), dtype=np.float32)]
    opt = AdamW(p, lr=1e-2)
    g = [np.ones((4, 4), dtype=np.float32)]
    opt.step(g)
    assert opt.t == 1
    m = opt.m[0]
    assert np.allclose(m, 0.1)


def test_adamw_weight_decay():
    np.random.seed(2)
    p = [np.ones((4, 4), dtype=np.float32)]
    opt = AdamW(p, lr=1e-2, weight_decay=0.1)
    g = [np.zeros((4, 4), dtype=np.float32)]
    new_params = opt.step(g)
    expected = np.ones((4, 4)) - 1e-2 * (0.1)
    assert np.allclose(new_params[0], expected, atol=1e-5)
