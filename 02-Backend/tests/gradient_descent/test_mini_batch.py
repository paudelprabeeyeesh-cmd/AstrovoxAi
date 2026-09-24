import pytest
from gradient_descent.mini_batch import MiniBatchGradientDescent


def _linear_loss(params, x, y):
    pred = [sum(p * xi for p, xi in zip(params, row)) for row in x]
    return sum((py - y_) ** 2 for py, y_ in zip(pred, y)) / len(y)


def _linear_grad(params, x, y):
    n = len(y)
    grads = [0.0] * len(params)
    for row, y_ in zip(x, y):
        pred = sum(p * xi for p, xi in zip(params, row))
        err = pred - y_
        for j, xi in enumerate(row):
            grads[j] += (2.0 / n) * err * xi
    return grads


def test_mini_batch_fit():
    x = [[1.0], [2.0], [3.0], [4.0]]
    y = [2.0, 4.0, 6.0, 8.0]
    opt = MiniBatchGradientDescent(
        params=[0.0],
        x=x,
        y=y,
        loss_fn=_linear_loss,
        grad_fn=_linear_grad,
        batch_size=2,
        lr=0.1,
        epochs=200,
        tol=1e-6,
    )
    result = opt.fit()
    assert abs(result[0] - 2.0) < 1e-3


def test_mini_batch_history():
    x = [[1.0], [2.0]]
    y = [3.0, 5.0]
    opt = MiniBatchGradientDescent(
        params=[0.0],
        x=x,
        y=y,
        loss_fn=_linear_loss,
        grad_fn=_linear_grad,
        batch_size=1,
        lr=0.1,
        epochs=10,
        tol=1e-6,
    )
    opt.fit()
    assert len(opt.loss_history) > 0
    assert opt.loss_history[0] > opt.loss_history[-1]


def test_mini_batch_small_batch_size():
    x = [[1.0, 1.0], [2.0, 2.0], [3.0, 3.0]]
    y = [2.0, 4.0, 6.0]
    opt = MiniBatchGradientDescent(
        params=[0.0, 0.0],
        x=x,
        y=y,
        loss_fn=_linear_loss,
        grad_fn=_linear_grad,
        batch_size=1,
        lr=0.05,
        epochs=300,
        tol=1e-6,
    )
    result = opt.fit()
    assert abs(result[0] - 1.0) < 1e-2
    assert abs(result[1] - 1.0) < 1e-2


def test_mini_batch_full_batch():
    x = [[1.0], [2.0], [3.0]]
    y = [2.0, 4.0, 6.0]
    opt = MiniBatchGradientDescent(
        params=[0.0],
        x=x,
        y=y,
        loss_fn=_linear_loss,
        grad_fn=_linear_grad,
        batch_size=3,
        lr=0.1,
        epochs=500,
        tol=1e-6,
    )
    result = opt.fit()
    assert abs(result[0] - 2.0) < 1e-2


def test_mini_batch_no_shuffle():
    x = [[1.0], [2.0], [3.0], [4.0]]
    y = [2.0, 4.0, 6.0, 8.0]
    opt = MiniBatchGradientDescent(
        params=[0.0],
        x=x,
        y=y,
        loss_fn=_linear_loss,
        grad_fn=_linear_grad,
        batch_size=2,
        lr=0.1,
        epochs=200,
        tol=1e-6,
        shuffle=False,
    )
    result = opt.fit()
    assert abs(result[0] - 2.0) < 1e-3


def test_mini_batch_tol_stops_early():
    x = [[1.0], [2.0]]
    y = [2.0, 4.0]
    opt = MiniBatchGradientDescent(
        params=[0.0],
        x=x,
        y=y,
        loss_fn=_linear_loss,
        grad_fn=_linear_grad,
        batch_size=1,
        lr=0.5,
        epochs=1000,
        tol=1e-6,
    )
    opt.fit()
    assert len(opt.loss_history) <= 1001
    assert opt.loss_history[0] > opt.loss_history[-1]


def test_mini_batch_single_param():
    x = [[1.0], [2.0]]
    y = [3.0, 5.0]
    opt = MiniBatchGradientDescent(
        params=[0.0],
        x=x,
        y=y,
        loss_fn=_linear_loss,
        grad_fn=_linear_grad,
        batch_size=1,
        lr=0.1,
        epochs=200,
        tol=1e-6,
    )
    result = opt.fit()
    assert abs(result[0] - 4.0) < 1e-2


def test_mini_batch_default_batch_size():
    x = [[1.0], [2.0]]
    y = [2.0, 4.0]
    opt = MiniBatchGradientDescent(
        params=[0.0],
        x=x,
        y=y,
        loss_fn=_linear_loss,
        grad_fn=_linear_grad,
    )
    assert opt.batch_size == 32


def test_mini_batch_default_epochs():
    x = [[1.0], [2.0]]
    y = [2.0, 4.0]
    opt = MiniBatchGradientDescent(
        params=[0.0],
        x=x,
        y=y,
        loss_fn=_linear_loss,
        grad_fn=_linear_grad,
    )
    assert opt.epochs == 100


def test_mini_batch_default_lr():
    x = [[1.0], [2.0]]
    y = [2.0, 4.0]
    opt = MiniBatchGradientDescent(
        params=[0.0],
        x=x,
        y=y,
        loss_fn=_linear_loss,
        grad_fn=_linear_grad,
    )
    assert opt.lr == 0.01


def test_mini_batch_history_length():
    x = [[1.0], [2.0]]
    y = [2.0, 4.0]
    opt = MiniBatchGradientDescent(
        params=[0.0],
        x=x,
        y=y,
        loss_fn=_linear_loss,
        grad_fn=_linear_grad,
        batch_size=1,
        lr=0.1,
        epochs=5,
        tol=1e-6,
        shuffle=False,
    )
    opt.fit()
    assert len(opt.loss_history) == 6
