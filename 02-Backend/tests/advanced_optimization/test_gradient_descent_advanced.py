import numpy as np
from advanced_optimization.gradient_descent_advanced import SGD, MomentumSGD, NesterovSGD, Adam


def test_sgd_step_changes_params():
    np.random.seed(0)
    p = [np.random.randn(4, 4).astype(np.float32)]
    opt = SGD(p, lr=1e-2)
    g = [np.random.randn(4, 4).astype(np.float32)]
    new_params = opt.step(g)
    assert not np.allclose(new_params[0], p[0])


def test_momentum_sgd_step():
    np.random.seed(1)
    p = [np.random.randn(4, 4).astype(np.float32)]
    opt = MomentumSGD(p, lr=1e-2, momentum=0.9)
    g = [np.random.randn(4, 4).astype(np.float32)]
    new_params = opt.step(g)
    assert new_params[0].shape == p[0].shape


def test_nesterov_sgd_step():
    np.random.seed(2)
    p = [np.random.randn(4, 4).astype(np.float32)]
    opt = NesterovSGD(p, lr=1e-2, momentum=0.9)
    g = [np.random.randn(4, 4).astype(np.float32)]
    new_params = opt.step(g)
    assert new_params[0].shape == p[0].shape


def test_adam_step_changes_params():
    np.random.seed(3)
    p = [np.random.randn(4, 4).astype(np.float32)]
    opt = Adam(p, lr=1e-3)
    g = [np.random.randn(4, 4).astype(np.float32)]
    new_params = opt.step(g)
    assert not np.allclose(new_params[0], p[0])


def test_adam_bias_correction():
    np.random.seed(4)
    p = [np.zeros((4, 4), dtype=np.float32)]
    opt = Adam(p, lr=1e-2)
    g = [np.ones((4, 4), dtype=np.float32)]
    opt.step(g)
    assert opt.t == 1
