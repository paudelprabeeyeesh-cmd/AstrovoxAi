import numpy as np
from proximal_algorithms.alternating_projection import alternating_projection


def test_alternating_projection_converges():
    proj_a = lambda x: [max(xi, 0.0) for xi in x]
    proj_b = lambda x: [xi / max(abs(xi), 1e-12) for xi in x]
    x = alternating_projection(proj_a, proj_b, [-1.0, 2.0], max_iter=100)
    assert abs(x[0]) < 1e-3
    assert abs(x[1] - 1.0) < 1e-3


def test_alternating_projection_identity():
    proj = lambda x: list(x)
    x = alternating_projection(proj, proj, [1.0, 2.0], max_iter=10)
    assert abs(x[0] - 1.0) < 1e-6
    assert abs(x[1] - 2.0) < 1e-6
