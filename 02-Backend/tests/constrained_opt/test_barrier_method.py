import numpy as np
from constrained_opt.barrier_method import barrier_method


def test_barrier_method_converges():
    f = lambda x: (x[0] - 2) ** 2 + (x[1] - 3) ** 2
    grad_f = lambda x: np.array([2 * (x[0] - 2), 2 * (x[1] - 3)])
    c = lambda x: x[0] + x[1] - 4
    x = barrier_method(f, grad_f, c, np.array([1.0, 1.0]), lr=0.1, max_iter=200)
    assert x[0] + x[1] - 4 >= -1.0
