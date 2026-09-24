import numpy as np
import pytest
from advanced_optimization.second_order import (
    newton_step_1d,
    newton_step_multi,
    damped_newton,
    bfgs,
)


def test_newton_step_1d_converges():
    f = lambda x: (x - 3) ** 2
    grad = lambda x: 2 * (x - 3)
    hess = lambda x: 2.0
    x = newton_step_1d(f, grad, hess, x0=0.0)
    assert abs(x - 3.0) < 1e-4


def test_newton_step_multi_converges():
    A = np.array([[2.0, 1.0], [1.0, 3.0]])
    b = np.array([1.0, 2.0])
    f = lambda x: 0.5 * x @ A @ x - b @ x
    grad = lambda x: A @ x - b
    hess = lambda x: A
    x0 = np.array([0.0, 0.0])
    x = newton_step_multi(x0, grad, hess)
    assert np.allclose(x, np.linalg.solve(A, b), atol=1e-4)


def test_damped_newton_step():
    A = np.array([[2.0, 1.0], [1.0, 3.0]])
    b = np.array([1.0, 2.0])
    grad = lambda x: A @ x - b
    hess = lambda x: A
    x = damped_newton(np.array([0.0, 0.0]), grad, hess)
    assert np.allclose(x, np.linalg.solve(A, b), atol=1e-3)


def test_bfgs_converges():
    A = np.array([[2.0, 0.0], [0.0, 3.0]])
    b = np.array([1.0, 2.0])
    grad = lambda x: A @ x - b
    x0 = np.array([5.0, 5.0])
    x = bfgs(x0, grad)
    assert np.allclose(x, np.linalg.solve(A, b), atol=1e-3)
