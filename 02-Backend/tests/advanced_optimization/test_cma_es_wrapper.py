import numpy as np
from advanced_optimization.cma_es_wrapper import cma_es_wrapper


def test_cma_es_wrapper_converges():
    f = lambda x: np.sum((x - 2) ** 2)
    x = cma_es_wrapper(f, np.array([0.0]), sigma=1.0, pop_size=20, max_iter=200)
    assert np.allclose(x, 2.0, atol=0.5)


def test_cma_es_wrapper_2d():
    f = lambda x: (x[0] - 1) ** 2 + (x[1] - 3) ** 2
    x = cma_es_wrapper(f, np.array([0.0, 0.0]), sigma=1.0, pop_size=20, max_iter=200)
    assert np.allclose(x, [1.0, 3.0], atol=0.5)


def test_cma_es_wrapper_bounded():
    f = lambda x: np.sum((x - 2) ** 2)
    bounds = [(-1.0, 1.0)]
    x = cma_es_wrapper(f, np.array([0.0]), sigma=1.0, pop_size=20, max_iter=200, bounds=bounds)
    assert -1.0 <= x[0] <= 1.0
