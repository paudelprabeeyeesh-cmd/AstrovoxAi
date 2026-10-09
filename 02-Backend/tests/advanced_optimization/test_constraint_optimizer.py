import numpy as np
from advanced_optimization.constraint_optimizer import (
    sqp,
    interior_point,
    active_set,
)


def test_sqp_converges():
    f = lambda x: (x[0] - 2) ** 2 + (x[1] - 3) ** 2
    grad_f = lambda x: np.array([2 * (x[0] - 2), 2 * (x[1] - 3)])
    c = lambda x: x[0] + x[1] - 4
    x = sqp(f, grad_f, [c], np.array([0.0, 0.0]), lr=0.1, max_iter=200)
    assert x[0] + x[1] - 4 >= -1.0


def test_interior_point_converges():
    f = lambda x: (x[0] - 2) ** 2 + (x[1] - 3) ** 2
    grad_f = lambda x: np.array([2 * (x[0] - 2), 2 * (x[1] - 3)])
    c = lambda x: -(x[0] + x[1] - 4)
    x = interior_point(f, grad_f, c, np.array([1.0, 1.0]), lr=0.1, max_iter=200)
    assert x[0] + x[1] - 4 >= -1.0


def test_active_set_converges():
    f = lambda x: (x[0] - 2) ** 2 + (x[1] - 3) ** 2
    grad_f = lambda x: np.array([2 * (x[0] - 2), 2 * (x[1] - 3)])
    c = lambda x: x[0] + x[1] - 4
    x = active_set(f, grad_f, [c], np.array([0.0, 0.0]), lr=0.1, max_iter=200)
    assert x[0] + x[1] - 4 >= -1.0
