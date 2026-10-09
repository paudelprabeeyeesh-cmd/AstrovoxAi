import numpy as np
from advanced_optimization.multi_fidelity_optimizer import (
    co_kriging,
    multi_fidelity_optimize,
)


def test_co_kriging_predicts():
    x_low = np.array([[0.0], [1.0], [2.0]])
    y_low = np.array([0.0, 1.0, 4.0])
    x_high = np.array([[1.5], [2.5]])
    y_high = np.array([2.25, 6.25])
    mean = co_kriging(x_low, y_low, x_high, y_high, np.array([1.0]), length_scale=1.0)
    assert isinstance(mean, float) or mean.size == 1


def test_multi_fidelity_optimize_returns_point():
    f_low = lambda x: (x[0] - 2) ** 2
    f_high = lambda x: (x[0] - 2) ** 2 + 0.1
    bounds = [(-10, 10)]
    x = multi_fidelity_optimize(f_low, f_high, bounds, n_low=10, n_high=5, max_iter=5)
    assert x.shape == (1,)
    assert -10 <= x[0] <= 10
