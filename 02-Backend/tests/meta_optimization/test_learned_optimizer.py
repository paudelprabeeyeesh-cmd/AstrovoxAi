import numpy as np
from advanced_optimization.meta_optimization.learned_optimizer import NeuralOptimizer, LSTMOptimizer


def test_neural_optimizer_step_changes_shape():
    np.random.seed(0)
    p = [np.random.randn(4, 4).astype(np.float32)]
    opt = NeuralOptimizer(np.prod(p[0].shape))
    g = [np.random.randn(4, 4).astype(np.float32)]
    new_params = opt.step(p, g)
    assert new_params[0].shape == p[0].shape


def test_neural_optimizer_step_modifies_params():
    np.random.seed(1)
    p = [np.random.randn(4, 4).astype(np.float32)]
    original = [np.copy(p_) for p_ in p]
    opt = NeuralOptimizer(np.prod(p[0].shape))
    g = [np.random.randn(4, 4).astype(np.float32)]
    new_params = opt.step(p, g)
    assert not np.allclose(new_params[0], original[0])


def test_neural_optimizer_t_increments():
    np.random.seed(2)
    p = [np.random.randn(4, 4).astype(np.float32)]
    opt = NeuralOptimizer(np.prod(p[0].shape))
    assert opt.t == 0
    g = [np.random.randn(4, 4).astype(np.float32)]
    opt.step(p, g)
    assert opt.t == 1


def test_lstm_optimizer_step_changes_shape():
    np.random.seed(3)
    p = [np.random.randn(4, 4).astype(np.float32)]
    opt = LSTMOptimizer(np.prod(p[0].shape))
    g = [np.random.randn(4, 4).astype(np.float32)]
    new_params = opt.step(p, g)
    assert new_params[0].shape == p[0].shape


def test_lstm_optimizer_step_modifies_params():
    np.random.seed(4)
    p = [np.random.randn(4, 4).astype(np.float32)]
    original = [np.copy(p_) for p_ in p]
    opt = LSTMOptimizer(np.prod(p[0].shape))
    g = [np.random.randn(4, 4).astype(np.float32)]
    new_params = opt.step(p, g)
    assert not np.allclose(new_params[0], original[0])


def test_lstm_optimizer_multi_param():
    np.random.seed(5)
    p = [np.random.randn(3, 3).astype(np.float32), np.random.randn(2).astype(np.float32)]
    opt = LSTMOptimizer(sum(int(np.prod(x.shape)) for x in p))
    g = [np.random.randn(3, 3).astype(np.float32), np.random.randn(2).astype(np.float32)]
    new_params = opt.step(p, g)
    assert new_params[0].shape == p[0].shape
    assert new_params[1].shape == p[1].shape


def test_neural_optimizer_multi_param():
    np.random.seed(6)
    p = [np.random.randn(3, 3).astype(np.float32), np.random.randn(2).astype(np.float32)]
    opt = NeuralOptimizer(sum(int(np.prod(x.shape)) for x in p))
    g = [np.random.randn(3, 3).astype(np.float32), np.random.randn(2).astype(np.float32)]
    new_params = opt.step(p, g)
    assert new_params[0].shape == p[0].shape
    assert new_params[1].shape == p[1].shape
