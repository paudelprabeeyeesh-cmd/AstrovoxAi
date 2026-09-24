import numpy as np
import pytest
from advanced_optimization.constrained_opt import (
    projected_gradient_descent,
    penalty_method,
)


def test_projected_gradient_descent():
    f = lambda x: np.sum((x - 1) ** 2)
    grad_f = lambda x: 2 * (x - 1)
    proj = lambda x: np.clip(x, 0, 10)
    x = projected_gradient_descent(f, grad_f, proj, np.array([5.0]), lr=0.1, max_iter=100)
    assert np.allclose(x, 1.0, atol=0.2)


def test_penalty_method():
    f = lambda x: (x[0] - 1) ** 2 + (x[1] - 2) ** 2
    grad_f = lambda x: np.array([2 * (x[0] - 1), 2 * (x[1] - 2)])
    c = lambda x: x[0] + x[1] - 3
    x = penalty_method(f, grad_f, [c], np.array([0.0, 0.0]), lr=0.01, max_iter=200)
    assert x[0] + x[1] - 3 >= -1.0
