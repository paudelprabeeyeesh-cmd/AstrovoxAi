import numpy as np
from advanced_optimization.black_box_optimizer import (
    powell_method,
    cma_es_simple,
    random_search,
)


def test_powell_method_converges():
    f = lambda x: np.sum((x - 3) ** 2)
    x = powell_method(f, np.array([0.0, 0.0]), max_iter=100)
    assert np.allclose(x, 3.0, atol=0.5)


def test_cma_es_simple_converges():
    f = lambda x: np.sum((x - 1) ** 2)
    x = cma_es_simple(f, np.array([0.0, 0.0]), sigma=1.0, pop_size=20, max_iter=50)
    assert np.allclose(x, 1.0, atol=0.5)


def test_random_search_converges():
    f = lambda x: np.sum((x - 2) ** 2)
    bounds = [(-10, 10), (-10, 10)]
    x = random_search(f, bounds, max_iter=200)
    assert np.allclose(x, 2.0, atol=1.0)
