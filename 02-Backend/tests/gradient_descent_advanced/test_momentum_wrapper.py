import numpy as np
from gradient_descent_advanced.momentum_wrapper import MomentumWrapper


def test_momentum_step_changes_params():
    np.random.seed(0)
    p = [np.random.randn(4, 4).astype(np.float32)]
    opt = MomentumWrapper(p, lr=1e-2, momentum=0.9)
    g = [np.random.randn(4, 4).astype(np.float32)]
    new_params = opt.step(g)
    assert not np.allclose(new_params[0], p[0])


def test_momentum_velocity_shape():
    np.random.seed(1)
    p = [np.random.randn(4, 4).astype(np.float32)]
    opt = MomentumWrapper(p, lr=1e-2, momentum=0.9)
    g = [np.random.randn(4, 4).astype(np.float32)]
    new_params = opt.step(g)
    assert new_params[0].shape == p[0].shape
    assert opt.velocity[0].shape == p[0].shape


def test_momentum_deterministic():
    np.random.seed(2)
    p = [np.random.randn(4, 4).astype(np.float32)]
    opt = MomentumWrapper(p, lr=1e-2, momentum=0.9)
    g = [np.ones((4, 4), dtype=np.float32)]
    opt.step(g)
    expected_velocity = 0.9 * np.zeros((4, 4)) + np.ones((4, 4))
    assert np.allclose(opt.velocity[0], expected_velocity)
