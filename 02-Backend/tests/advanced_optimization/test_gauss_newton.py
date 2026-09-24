from advanced_optimization.gauss_newton import gauss_newton


def test_gauss_newton_linear_residual():
    residual_fn = lambda x: [x[0] - 1.0, x[1] - 2.0]
    jacobian_fn = lambda x: [[1.0, 0.0], [0.0, 1.0]]
    x = gauss_newton(residual_fn, jacobian_fn, [0.0, 0.0])
    assert abs(x[0] - 1.0) < 1e-4
    assert abs(x[1] - 2.0) < 1e-4


def test_gauss_newton_nonlinear_residual():
    def residual_fn(x):
        a, b = x
        return [a * (b ** 1) - 2.0, a * (b ** 2) - 8.0]
    def jacobian_fn(x):
        a, b = x
        return [[b, a], [b ** 2, 2 * a * b]]
    x = gauss_newton(residual_fn, jacobian_fn, [1.0, 1.0])
    r = residual_fn(x)
    assert abs(r[0]) < 1e-3
    assert abs(r[1]) < 1e-3


def test_gauss_newton_returns_list():
    residual_fn = lambda x: [x[0]]
    jacobian_fn = lambda x: [[1.0]]
    x = gauss_newton(residual_fn, jacobian_fn, [0.0])
    assert isinstance(x, list)
