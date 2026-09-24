import numpy as np
from constrained_opt.augmented_lagrangian import augmented_lagrangian


def test_augmented_lagrangian_converges():
    f = lambda x: (x[0] - 2) ** 2 + (x[1] - 3) ** 2
    grad_f = lambda x: np.array([2 * (x[0] - 2), 2 * (x[1] - 3)])
    c = lambda x: x[0] + x[1] - 4
    x = augmented_lagrangian(f, grad_f, [c], np.array([0.0, 0.0]), lr=0.1, max_iter=200)
    assert x[0] + x[1] - 4 >= -1.0
