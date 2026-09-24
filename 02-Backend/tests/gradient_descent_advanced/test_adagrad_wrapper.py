import numpy as np
from gradient_descent_advanced.adagrad_wrapper import AdagradWrapper


def test_adagrad_step_changes_params():
    np.random.seed(0)
    p = [np.random.randn(4, 4).astype(np.float32)]
    opt = AdagradWrapper(p, lr=1e-2)
    g = [np.random.randn(4, 4).astype(np.float32)]
    new_params = opt.step(g)
    assert not np.allclose(new_params[0], p[0])


def test_adagrad_sum_shape():
    np.random.seed(1)
    p = [np.random.randn(4, 4).astype(np.float32)]
    opt = AdagradWrapper(p, lr=1e-2)
    g = [np.random.randn(4, 4).astype(np.float32)]
    new_params = opt.step(g)
    assert new_params[0].shape == p[0].shape
    assert opt.sum[0].shape == p[0].shape


def test_adagrad_deterministic():
    np.random.seed(2)
    p = [np.ones((4, 4), dtype=np.float32)]
    opt = AdagradWrapper(p, lr=1e-2)
    g = [np.ones((4, 4), dtype=np.float32)]
    opt.step(g)
    expected_sum = np.ones((4, 4)) ** 2
    assert np.allclose(opt.sum[0], expected_sum)
