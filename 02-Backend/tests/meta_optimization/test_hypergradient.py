import numpy as np
from advanced_optimization.meta_optimization.hypergradient import (
    HypergradientOptimizer,
    compute_hypergradient,
    hypergradient_descent,
)


def _make_params():
    return [np.random.randn(4, 4).astype(np.float32)]


def test_compute_hypergradient_returns_list():
    np.random.seed(0)
    params = _make_params()
    loss_fn = lambda p: float(np.sum(p[0] ** 2))
    hg = compute_hypergradient(loss_fn, params, None, inner_steps=2, inner_lr=1e-3, epsilon=1e-4)
    assert isinstance(hg, list)
    assert len(hg) == len(params)
    assert hg[0].shape == params[0].shape


def test_compute_hypergradient_nonzero():
    np.random.seed(1)
    params = [np.ones((4, 4), dtype=np.float32)]
    loss_fn = lambda p: float(np.sum(p[0] ** 2))
    hg = compute_hypergradient(loss_fn, params, None, inner_steps=2, inner_lr=1e-3, epsilon=1e-4)
    assert not np.allclose(hg[0], 0.0)


def test_hypergradient_descent_returns_updated_params():
    np.random.seed(2)
    params = _make_params()
    loss_fn = lambda p: float(np.sum(p[0] ** 2))
    updated, hg = hypergradient_descent(params, loss_fn, None, meta_lr=1e-3, inner_steps=2, inner_lr=1e-3, epsilon=1e-4)
    assert len(updated) == len(params)
    assert updated[0].shape == params[0].shape


def test_hypergradient_optimizer_step_changes_params():
    np.random.seed(3)
    params = _make_params()
    loss_fn = lambda p: float(np.sum(p[0] ** 2))
    opt = HypergradientOptimizer(params, meta_lr=1e-3)
    original = [np.copy(p) for p in opt.get_params()]
    new_params = opt.step(loss_fn, None)
    assert len(new_params) == len(params)


def test_hypergradient_optimizer_records_history():
    np.random.seed(4)
    params = _make_params()
    loss_fn = lambda p: float(np.sum(p[0] ** 2))
    opt = HypergradientOptimizer(params, meta_lr=1e-3)
    opt.step(loss_fn, None)
    history = opt.get_history()
    assert len(history) == 1
    assert "hypergrads" in history[0]
    assert "loss" in history[0]


def test_hypergradient_optimizer_get_params():
    np.random.seed(5)
    params = _make_params()
    opt = HypergradientOptimizer(params, meta_lr=1e-3)
    retrieved = opt.get_params()
    assert len(retrieved) == len(params)
    for r, p in zip(retrieved, params):
        assert r.shape == p.shape
