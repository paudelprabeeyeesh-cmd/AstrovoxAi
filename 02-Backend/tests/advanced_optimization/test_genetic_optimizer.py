import math
from advanced_optimization.genetic_optimizer import genetic_algorithm


def _sum_sq(x, target):
    return sum((xi - t) ** 2 for xi, t in zip(x, target))


def test_genetic_algorithm_converges():
    target = [3.0]
    f = lambda x: _sum_sq(x, target)
    x = genetic_algorithm(f, [(-10, 10)], pop_size=50, max_iter=100)
    assert abs(x[0] - target[0]) < 0.5


def test_genetic_algorithm_multidim():
    target = [2.0, -1.0]
    f = lambda x: _sum_sq(x, target)
    x = genetic_algorithm(f, [(-5, 5), (-5, 5)], pop_size=50, max_iter=100)
    assert all(abs(xi - ti) < 0.5 for xi, ti in zip(x, target))
