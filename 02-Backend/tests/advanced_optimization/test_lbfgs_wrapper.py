from advanced_optimization.lbfgs_wrapper import lbfgs


def test_lbfgs_converges_1d():
    f = lambda x: (x[0] - 3) ** 2
    grad = lambda x: [2 * (x[0] - 3)]
    x = lbfgs(f, grad, [0.0])
    assert abs(x[0] - 3.0) < 1e-4


def test_lbfgs_converges_2d():
    A = [[2.0, 0.0], [0.0, 3.0]]
    b = [1.0, 2.0]
    f = lambda x: 0.5 * (A[0][0] * x[0] ** 2 + A[1][1] * x[1] ** 2) - (b[0] * x[0] + b[1] * x[1])
    grad = lambda x: [A[0][0] * x[0] - b[0], A[1][1] * x[1] - b[1]]
    x = lbfgs(f, grad, [5.0, 5.0])
    assert abs(x[0] - 0.5) < 1e-3
    assert abs(x[1] - 2.0 / 3.0) < 1e-3


def test_lbfgs_returns_list():
    f = lambda x: sum((xi - 1) ** 2 for xi in x)
    grad = lambda x: [2 * (xi - 1) for xi in x]
    x = lbfgs(f, grad, [0.0, 0.0])
    assert isinstance(x, list)
