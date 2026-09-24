import numpy as np
from gradient_descent_advanced.adam_wrapper import AdamWrapper


def test_adam_step_changes_params():
    np.random.seed(0)
    p = [np.random.randn(4, 4).astype(np.float32)]
    opt = AdamWrapper(p, lr=1e-3)
    g = [np.random.randn(4, 4).astype(np.float32)]
    new_params = opt.step(g)
    assert not np.allclose(new_params[0], p[0])


def test_adam_bias_correction():
    np.random.seed(1)
    p = [np.zeros((4, 4), dtype=np.float32)]
    opt = AdamWrapper(p, lr=1e-2)
    g = [np.ones((4, 4), dtype=np.float32)]
    opt.step(g)
    assert opt.t == 1
    m = opt.m[0]
    assert np.allclose(m, 0.1)


def test_adam_param_shape():
    np.random.seed(2)
    p = [np.random.randn(4, 4).astype(np.float32)]
    opt = AdamWrapper(p, lr=1e-3)
    g = [np.random.randn(4, 4).astype(np.float32)]
    new_params = opt.step(g)
    assert new_params[0].shape == p[0].shape
