import numpy as np
from advanced_optimization.meta_optimization.warm_starting import (
    WarmStartStrategy,
    warm_start_from_params,
    warm_start_adam_state,
    interpolate_initialization,
)


def test_warm_start_from_params_copies_shape():
    np.random.seed(0)
    source = [np.random.randn(8).astype(np.float32)]
    target_shapes = [(4, 4)]
    result = warm_start_from_params(source, lambda: target_shapes, scale=1.0)
    assert len(result) == 1
    assert result[0].shape == (4, 4)


def test_warm_start_from_params_scales():
    np.random.seed(1)
    source = [np.ones(4, dtype=np.float32)]
    result = warm_start_from_params(source, lambda: [(2, 2)], scale=2.0)
    assert np.allclose(result[0], 2.0)


def test_warm_start_from_params_pads_with_tile():
    np.random.seed(2)
    source = [np.array([1.0, 2.0], dtype=np.float32)]
    result = warm_start_from_params(source, lambda: [(3, 2)], scale=1.0)
    assert result[0].shape == (3, 2)


def test_warm_start_adam_state_returns_dict():
    np.random.seed(3)
    params = [np.zeros((4, 4), dtype=np.float32)]
    state = warm_start_adam_state(params)
    assert "m" in state and "v" in state and "t" in state
    assert state["t"] == 0
    assert len(state["m"]) == 1
    assert state["m"][0].shape == params[0].shape


def test_warm_start_adam_state_correct_keys():
    params = [np.zeros((2, 2), dtype=np.float32)]
    state = warm_start_adam_state(params, beta1=0.8, beta2=0.9, eps=1e-7)
    assert state["beta1"] == 0.8
    assert state["beta2"] == 0.9
    assert state["eps"] == 1e-7


def test_interpolate_initialization_midpoint():
    np.random.seed(4)
    base = [np.ones((3, 3), dtype=np.float32)]
    fine = [np.zeros((3, 3), dtype=np.float32)]
    result = interpolate_initialization(base, fine, alpha=0.5)
    assert np.allclose(result[0], 0.5)


def test_interpolate_initialization_alpha_one():
    np.random.seed(5)
    base = [np.random.randn(3, 3).astype(np.float32)]
    fine = [np.random.randn(3, 3).astype(np.float32)]
    result = interpolate_initialization(base, fine, alpha=1.0)
    assert np.allclose(result[0], base[0])


def test_warm_start_strategy_copy():
    np.random.seed(6)
    source = [np.random.randn(4, 4).astype(np.float32)]
    strategy = WarmStartStrategy(source, strategy="copy")
    target = [np.zeros((4, 4), dtype=np.float32)]
    result = strategy.initialize(target)
    assert np.allclose(result[0], source[0])


def test_warm_start_strategy_zeros():
    strategy = WarmStartStrategy([], strategy="zeros")
    target = [np.ones((3, 3), dtype=np.float32)]
    result = strategy.initialize(target)
    assert np.allclose(result[0], 0.0)


def test_warm_start_strategy_random():
    np.random.seed(7)
    strategy = WarmStartStrategy([], strategy="random", scale=0.5)
    target = [np.zeros((2, 2), dtype=np.float32)]
    result = strategy.initialize(target)
    assert result[0].shape == (2, 2)
    assert not np.allclose(result[0], 0.0)


def test_warm_start_strategy_invalid():
    strategy = WarmStartStrategy([], strategy="unknown")
    target = [np.zeros((2, 2), dtype=np.float32)]
    try:
        strategy.initialize(target)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
