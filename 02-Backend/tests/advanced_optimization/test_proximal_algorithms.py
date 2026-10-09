import numpy as np
from advanced_optimization.proximal_algorithms import (
    proximal_gradient,
    ista,
    fista,
    admm,
    soft_threshold,
)


def test_soft_threshold():
    x = np.array([2.0, -2.0, 0.5, -0.5])
    y = soft_threshold(x, 1.0)
    assert np.allclose(y, np.array([1.0, -1.0, 0.0, 0.0]))


def test_proximal_gradient_lasso():
    f = lambda x: 0.5 * np.sum((x - 2) ** 2)
    grad_f = lambda x: x - 2
    prox = lambda x, t: soft_threshold(x, 0.1 * t)
    x = proximal_gradient(f, grad_f, prox, np.array([0.0]), lr=0.1, max_iter=100)
    assert abs(x[0] - 2.0) < 0.5


def test_ista_runs():
    f = lambda x: 0.5 * np.sum((x - 1) ** 2)
    grad_f = lambda x: x - 1
    prox = lambda x, t: soft_threshold(x, 0.1 * t)
    x = ista(f, grad_f, prox, np.array([0.0]), lr=0.1, max_iter=100)
    assert abs(x[0] - 1.0) < 0.5


def test_fista_runs():
    f = lambda x: 0.5 * np.sum((x - 1) ** 2)
    grad_f = lambda x: x - 1
    prox = lambda x, t: soft_threshold(x, 0.1 * t)
    x = fista(f, grad_f, prox, np.array([0.0]), lr=0.1, max_iter=100)
    assert abs(x[0] - 1.0) < 0.5


def test_admm_runs():
    f = lambda x: 0.5 * np.sum((x - 1) ** 2)
    grad_f = lambda x: x - 1
    prox = lambda x, t: soft_threshold(x, 0.1 * t)
    x = admm(f, grad_f, prox, np.array([0.0]), np.array([0.0]), np.array([0.0]), max_iter=100)
    assert abs(x[0] - 1.0) < 0.5
