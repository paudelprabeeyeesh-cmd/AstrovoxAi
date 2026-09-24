import pytest
from gradient_descent.sgd import SGD


def test_sgd_step_changes_params():
    params = [1.0, -2.0, 3.0]
    opt = SGD(params, lr=0.1)
    grads = [0.5, -1.0, 0.2]
    new_params = opt.step(grads)
    assert new_params == [0.95, -1.9, 2.98]
    assert opt.params == [0.95, -1.9, 2.98]


def test_sgd_default_lr():
    opt = SGD([1.0, 2.0])
    assert opt.lr == 0.01


def test_sgd_multiple_steps():
    opt = SGD([1.0], lr=0.1)
    opt.step([2.0])
    opt.step([2.0])
    assert abs(opt.params[0] - 0.6) < 1e-9


def test_sgd_returns_new_list():
    params = [1.0, 2.0]
    opt = SGD(params, lr=0.1)
    new_params = opt.step([0.1, 0.1])
    assert new_params is not opt.params
