import math

import numpy as np
from proximal_algorithms.ista_wrapper import ista


def soft_threshold(x, threshold):
    return [math.copysign(max(abs(xi) - threshold, 0.0), xi) for xi in x]


def test_ista_runs():
    f = lambda x: 0.5 * sum((xi - 1.0) ** 2 for xi in x)
    grad_f = lambda x: [xi - 1.0 for xi in x]
    prox = lambda x, t: soft_threshold(x, 0.1 * t)
    x = ista(f, grad_f, prox, [0.0], lr=0.1, max_iter=100)
    assert abs(x[0] - 1.0) < 0.5


def test_ista_converges():
    f = lambda x: 0.5 * sum(xi ** 2 for xi in x)
    grad_f = lambda x: list(x)
    prox = lambda x, t: [0.0 for _ in x]
    x = ista(f, grad_f, prox, [5.0, -3.0], lr=0.5, max_iter=500)
    assert all(abs(xi) < 1e-4 for xi in x)
