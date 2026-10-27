"""Unit tests for Section 6 calculus + Section 7 optimization."""

from math_engine.calculus.differentiation import (
    derivative, chain_rule, partial_derivative, gradient, hessian,
    taylor_series, integrate, autograd_demo,
)
from math_engine.optimization.gradient_descent import (
    gradient_descent, adam_step, lagrange_demo, fib_dp, convergence_check,
)


def test_derivative():
    r = derivative("x**2", "x", point=3)
    assert abs(r.result["value_at_point"] - 6.0) < 1e-6
    assert r.result["matches"] is True


def test_chain_rule():
    r = chain_rule("u**2", "x**3", "x")
    assert r.ok()


def test_gradient():
    r = gradient("x**2 + y**2", ["x", "y"])
    assert "gradient" in r.result


def test_hessian():
    r = hessian("x**2 + y**2", ["x", "y"])
    assert r.ok()


def test_integrate():
    r = integrate("x", "x", 0, 1)
    assert abs(r.result["integral"] - 0.5) < 1e-9


def test_taylor():
    r = taylor_series("exp(x)", "x", 0, 4)
    assert r.ok()


def test_autograd_demo():
    def f(p): return p[0] ** 2 + p[1] ** 2
    r = autograd_demo(f, [3.0, 4.0])
    assert abs(r.result["gradient"][0] - 6.0) < 1e-4


def test_gradient_descent():
    def grad(x): return [2 * x[0], 2 * x[1]]
    r = gradient_descent(grad, [5.0, 5.0], lr=0.1)
    assert abs(r.result["solution"][0]) < 0.5


def test_adam_step():
    r = adam_step([1.0], [0.5], t=1)
    assert r.ok()


def test_fib_dp():
    assert fib_dp(10).result["result"] == 55


def test_convergence_check():
    assert convergence_check([1.0, 1.0001, 1.00001], tol=1e-3).result["converged"]
