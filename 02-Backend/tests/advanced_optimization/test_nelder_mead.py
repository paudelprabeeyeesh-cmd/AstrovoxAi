import numpy as np
from advanced_optimization.nelder_mead import nelder_mead


def test_nelder_mead_converges():
    f = lambda x: np.sum((x - 3) ** 2)
    x0 = [np.array([0.0]), np.array([5.0]), np.array([1.0])]
    x = nelder_mead(f, x0, max_iter=5000)
    assert np.allclose(x, 3.0, atol=0.5)


def test_nelder_mead_2d():
    f = lambda x: (x[0] - 1) ** 2 + (x[1] - 2) ** 2
    x0 = [np.array([0.0, 0.0]), np.array([1.0, 0.0]), np.array([0.0, 1.0])]
    x = nelder_mead(f, x0, max_iter=5000)
    assert np.allclose(x, [1.0, 2.0], atol=0.5)
