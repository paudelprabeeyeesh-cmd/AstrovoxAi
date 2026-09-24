import math

from coordinate_descent.stochastic_coordinate import stochastic_coordinate_descent


def test_stochastic_coordinate_descent():
    f = lambda x: sum((xi - 2.0) ** 2 for xi in x)
    grad_f = lambda x: [2.0 * (xi - 2.0) for xi in x]
    x = stochastic_coordinate_descent(f, grad_f, [0.0], max_iter=200, seed=42)
    assert math.isclose(x[0], 2.0, abs_tol=0.1)


def test_stochastic_coordinate_descent_reproducible():
    x1 = stochastic_coordinate_descent(
        lambda x: sum((xi - 1.0) ** 2 for xi in x),
        lambda x: [2.0 * (xi - 1.0) for xi in x],
        [0.0],
        max_iter=50,
        seed=123,
    )
    x2 = stochastic_coordinate_descent(
        lambda x: sum((xi - 1.0) ** 2 for xi in x),
        lambda x: [2.0 * (xi - 1.0) for xi in x],
        [0.0],
        max_iter=50,
        seed=123,
    )
    assert x1 == x2
