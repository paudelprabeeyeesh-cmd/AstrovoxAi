import math
from advanced_optimization.simulated_annealing import simulated_annealing


def _sum_sq(x, target):
    return sum((xi - target) ** 2 for xi in x)


def test_simulated_annealing_converges():
    target = 3.0
    f = lambda x: _sum_sq(x, target)
    x = simulated_annealing(f, [0.0], max_iter=2000)
    assert abs(x[0] - target) < 0.5


def test_simulated_annealing_with_bounds():
    target = 2.0
    f = lambda x: _sum_sq(x, target)
    x = simulated_annealing(f, [0.0], bounds=[(-5, 5)], max_iter=2000)
    assert abs(x[0] - target) < 0.5
