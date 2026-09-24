import pytest
from gradient_descent.batch_gradient import BatchGradientDescent


def _quadratic_loss(params):
    x, y = params
    return x ** 2 + y ** 2


def _quadratic_grad(params):
    x, y = params
    return [2.0 * x, 2.0 * y]


def test_batch_gradient_descent_converges():
    opt = BatchGradientDescent(
        params=[3.0, -4.0],
        loss_fn=_quadratic_loss,
        grad_fn=_quadratic_grad,
        lr=0.1,
        max_iter=1000,
        tol=1e-6,
    )
    result = opt.fit()
    assert abs(result[0]) < 1e-4
    assert abs(result[1]) < 1e-4
    assert len(opt.loss_history) > 0
    assert opt.loss_history[0] > opt.loss_history[-1]


def test_batch_gradient_descent_max_iter():
    call_count = [0]

    def loss_fn(p):
        call_count[0] += 1
        return sum(v * v for v in p)

    def grad_fn(p):
        return [2.0 * v for v in p]

    opt = BatchGradientDescent(
        params=[1.0],
        loss_fn=loss_fn,
        grad_fn=grad_fn,
        lr=0.1,
        max_iter=5,
        tol=1e-12,
    )
    result = opt.fit()
    assert call_count[0] <= 10
    assert len(opt.loss_history) <= 6


def test_batch_gradient_descent_does_not_diverged():
    opt = BatchGradientDescent(
        params=[1.0, 1.0],
        loss_fn=_quadratic_loss,
        grad_fn=_quadratic_grad,
        lr=0.05,
        max_iter=50,
        tol=1e-6,
    )
    result = opt.fit()
    assert all(abs(v) < 10 for v in result)
