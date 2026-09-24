import numpy as np
import pytest
from advanced_optimization.meta_optimization import LearnedOptimizer, SimpleLSTMOptimizer


def test_learned_optimizer_step():
    np.random.seed(0)
    p = [np.random.randn(4, 4).astype(np.float32)]
    opt = LearnedOptimizer(np.prod(p[0].shape))
    g = [np.random.randn(4, 4).astype(np.float32)]
    new_params = opt.step(p, g, lr=1e-3)
    assert new_params[0].shape == p[0].shape


def test_lstm_optimizer_step():
    np.random.seed(1)
    p = [np.random.randn(4, 4).astype(np.float32)]
    opt = SimpleLSTMOptimizer(np.prod(p[0].shape))
    g = [np.random.randn(4, 4).astype(np.float32)]
    new_params = opt.step(p, g)
    assert new_params[0].shape == p[0].shape
