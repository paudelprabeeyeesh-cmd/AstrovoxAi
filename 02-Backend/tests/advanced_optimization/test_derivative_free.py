import numpy as np
from advanced_optimization.derivative_free import (
    nelder_ead,
    pattern_search,
    differential_evolution,
)


def test_nelder_ead_converges():
    f = lambda x: np.sum((x - 3) ** 2)
    x0 = [np.array([0.0]), np.array([5.0]), np.array([1.0])]
    x = nelder_ead(f, x0, max_iter=5000)
    assert np.allclose(x, 3.0, atol=0.5)


def test_pattern_search_converges():
    f = lambda x: np.sum((x - 2) ** 2)
    x = pattern_search(f, np.array([0.0]), step_size=1.0, max_iter=100)
    assert np.allclose(x, 2.0, atol=0.5)


def test_differential_evolution_converges():
    f = lambda x: np.sum((x - 1) ** 2)
    bounds = [(-5, 5), (-5, 5)]
    x = differential_evolution(f, bounds, pop_size=20, max_iter=50)
    assert np.allclose(x, 1.0, atol=0.5)
