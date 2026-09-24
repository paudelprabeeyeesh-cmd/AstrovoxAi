import numpy as np
from advanced_optimization.bayesian_optimization import (
    bayesian_optimization,
    gaussian_process,
    expected_improvement,
)


def test_gaussian_process_predicts():
    x_train = np.array([[0.0], [1.0], [2.0], [3.0]])
    y_train = np.array([0.0, 1.0, 4.0, 9.0])
    mean, var = gaussian_process(x_train, y_train, np.array([1.5]), length_scale=1.0)
    assert isinstance(mean, float) or mean.size == 1
    assert isinstance(var, float) or var.size == 1
    assert var > 0


def test_expected_improvement_positive():
    mean = 1.0
    var = 0.5
    best_f = 0.5
    ei = expected_improvement(mean, var, best_f)
    assert ei > 0


def test_bayesian_optimization_finds_minimum():
    f = lambda x: (x[0] - 2) ** 2
    bounds = [(-10, 10)]
    x = bayesian_optimization(f, bounds, n_init=5, n_iter=10, length_scale=1.0)
    assert abs(x[0] - 2.0) < 1.0
