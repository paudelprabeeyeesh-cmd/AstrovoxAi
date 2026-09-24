import numpy as np
from proximal_algorithms.DouglasRachford import douglas_rachford


def test_douglas_rachford_runs():
    prox_a = lambda x, t: [xi / 2.0 for xi in x]
    prox_b = lambda x, t: [xi / 2.0 for xi in x]
    x = douglas_rachford(prox_a, prox_b, [4.0], max_iter=100)
    assert abs(x[0]) < 1e-3


def test_douglas_rachford_zero():
    prox_a = lambda x, t: [xi / 2.0 for xi in x]
    prox_b = lambda x, t: [0.0 for _ in x]
    x = douglas_rachford(prox_a, prox_b, [5.0, -3.0], max_iter=100)
    assert abs(x[0]) < 1e-3
    assert abs(x[1]) < 1e-3
