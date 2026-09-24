import numpy as np
from advanced_optimization.genetic_optimizer import genetic_algorithm


def test_genetic_algorithm_converges():
    f = lambda x: np.sum((np.asarray(x) - 3) ** 2)
    x = genetic_algorithm(f, [(-10, 10)], pop_size=50, max_iter=50)
    assert np.allclose(x, 3.0, atol=0.5)


def test_genetic_algorithm_multidim():
    f = lambda x: np.sum((np.asarray(x) - np.array([2.0, -1.0])) ** 2)
    x = genetic_algorithm(f, [(-5, 5), (-5, 5)], pop_size=50, max_iter=50)
    assert np.allclose(x, [2.0, -1.0], atol=0.5)
