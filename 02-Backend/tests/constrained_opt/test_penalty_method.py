import numpy as np
from constrained_opt.penalty_method import penalty_method


def test_penalty_method_converges():
    f = lambda x: (x[0] - 1) ** 2 + (x[1] - 2) ** 2
    grad_f = lambda x: np.array([2 * (x[0] - 1), 2 * (x[1] - 2)])
    c = lambda x: x[0] + x[1] - 3
    x = penalty_method(f, grad_f, [c], np.array([0.0, 0.0]), lr=0.01, max_iter=200)
    assert x[0] + x[1] - 3 >= -1.0
