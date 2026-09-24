import numpy as np
from gradient_descent_advanced.rmsprop_wrapper import RMSPropWrapper


def test_rmsprop_step_changes_params():
    np.random.seed(0)
    p = [np.random.randn(4, 4).astype(np.float32)]
    opt = RMSPropWrapper(p, lr=1e-2, alpha=0.99)
    g = [np.random.randn(4, 4).astype(np.float32)]
    new_params = opt.step(g)
    assert not np.allclose(new_params[0], p[0])


def test_rmsprop_cache_shape():
    np.random.seed(1)
    p = [np.random.randn(4, 4).astype(np.float32)]
    opt = RMSPropWrapper(p, lr=1e-2, alpha=0.99)
    g = [np.random.randn(4, 4).astype(np.float32)]
    new_params = opt.step(g)
    assert new_params[0].shape == p[0].shape
    assert opt.cache[0].shape == p[0].shape


def test_rmsprop_deterministic():
    np.random.seed(2)
    p = [np.ones((4, 4), dtype=np.float32)]
    opt = RMSPropWrapper(p, lr=1e-2, alpha=0.99)
    g = [np.ones((4, 4), dtype=np.float32)]
    opt.step(g)
    expected_cache = 0.99 * np.zeros((4, 4)) + 0.01 * np.ones((4, 4)) ** 2
    assert np.allclose(opt.cache[0], expected_cache)
