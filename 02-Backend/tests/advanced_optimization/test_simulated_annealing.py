import numpy as np
from advanced_optimization.simulated_annealing import simulated_annealing


def test_simulated_annealing_converges():
    f = lambda x: np.sum((x - 3) ** 2)
    x = simulated_annealing(f, np.array([0.0]), max_iter=1000)
    assert np.allclose(x, 3.0, atol=0.5)


def test_simulated_annealing_with_bounds():
    f = lambda x: np.sum((x - 2) ** 2)
    x = simulated_annealing(f, np.array([0.0]), bounds=[(-5, 5)], max_iter=1000)
    assert np.allclose(x, 2.0, atol=0.5)
