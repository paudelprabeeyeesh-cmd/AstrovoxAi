import numpy as np
from advanced_optimization.ant_colony_optimizer import ant_colony_optimization


def test_ant_colony_optimization_converges():
    f = lambda x: np.sum((np.asarray(x) - 3) ** 2)
    x = ant_colony_optimization(f, [(-10, 10)], n_ants=20, max_iter=50)
    assert np.allclose(x, 3.0, atol=0.5)


def test_ant_colony_optimization_multidim():
    f = lambda x: np.sum((np.asarray(x) - np.array([2.0, -1.0])) ** 2)
    x = ant_colony_optimization(f, [(-5, 5), (-5, 5)], n_ants=20, max_iter=50)
    assert np.allclose(x, [2.0, -1.0], atol=0.5)
