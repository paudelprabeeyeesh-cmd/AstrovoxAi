from advanced_optimization.natural_gradient import (
    natural_gradient_step,
    natural_gradient_descent,
)


def test_natural_gradient_step():
    grad = lambda x: [2 * (x[0] - 1), 2 * (x[1] - 2)]
    fisher_diag = lambda x: [1.0, 1.0]
    x = [0.0, 0.0]
    x_new = natural_gradient_step(x, grad, fisher_diag, step_size=0.1)
    assert isinstance(x_new, list)
    assert len(x_new) == 2


def test_natural_gradient_descent_converges():
    grad = lambda x: [2 * (x[0] - 1), 2 * (x[1] - 2)]
    fisher_diag = lambda x: [1.0, 1.0]
    x = natural_gradient_descent(lambda x: 0, grad, fisher_diag, [0.0, 0.0])
    assert abs(x[0] - 1.0) < 1e-2
    assert abs(x[1] - 2.0) < 1e-2


def test_natural_gradient_step_diagonal_fisher():
    grad = lambda x: [4 * (x[0] - 1), 2 * (x[1] - 3)]
    fisher_diag = lambda x: [2.0, 1.0]
    x = [0.0, 0.0]
    x_new = natural_gradient_step(x, grad, fisher_diag, step_size=0.1)
    expected = [0.2, 0.6]
    assert abs(x_new[0] - expected[0]) < 1e-6
    assert abs(x_new[1] - expected[1]) < 1e-6
