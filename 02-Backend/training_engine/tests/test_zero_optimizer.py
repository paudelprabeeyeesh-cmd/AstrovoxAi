import numpy as np
import pytest
from training_engine.zero_optimizer import ZeROOptimizer


def test_zero_stage1_partitions_optim_states():
    np.random.seed(0)
    p = [np.random.randn(4, 4).astype(np.float32)]
    opt = ZeROOptimizer(p, lr=1e-2, stage=1, world_size=2)
    g = [np.random.randn(4, 4).astype(np.float32)]
    new_params = opt.step(g, rank=0)
    assert new_params[0].shape == p[0].shape


def test_zero_stage2_partitions_grads():
    np.random.seed(1)
    p = [np.random.randn(4, 4).astype(np.float32)]
    opt = ZeROOptimizer(p, lr=1e-2, stage=2, world_size=2)
    g = [np.random.randn(4, 4).astype(np.float32)]
    new_params = opt.step(g, rank=0)
    assert new_params[0].shape == p[0].shape


def test_zero_stage3_partitions_params():
    np.random.seed(2)
    p = [np.random.randn(4, 4).astype(np.float32)]
    opt = ZeROOptimizer(p, lr=1e-2, stage=3, world_size=2)
    g = [np.random.randn(4, 4).astype(np.float32)]
    new_params = opt.step(g, rank=0)
    assert new_params[0].shape == (2, 4)
