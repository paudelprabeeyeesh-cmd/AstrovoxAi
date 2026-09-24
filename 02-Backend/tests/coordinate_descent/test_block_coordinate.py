import math

from coordinate_descent.block_coordinate import block_coordinate_descent


def test_block_coordinate_descent():
    f = lambda x: sum((xi - 1.0) ** 2 for xi in x)
    grad_f = lambda x: [2.0 * (xi - 1.0) for xi in x]
    x = block_coordinate_descent(f, grad_f, [0.0, 0.0], blocks=[[0], [1]], max_iter=200)
    assert math.isclose(x[0], 1.0, abs_tol=0.1)
    assert math.isclose(x[1], 1.0, abs_tol=0.1)


def test_block_coordinate_descent_single_block():
    f = lambda x: sum((xi - 2.0) ** 2 for xi in x)
    grad_f = lambda x: [2.0 * (xi - 2.0) for xi in x]
    x = block_coordinate_descent(f, grad_f, [0.0, 0.0], blocks=[[0, 1]], max_iter=200)
    assert math.isclose(x[0], 2.0, abs_tol=0.1)
    assert math.isclose(x[1], 2.0, abs_tol=0.1)
