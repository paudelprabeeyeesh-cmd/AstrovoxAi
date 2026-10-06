"""Tests for distributed training and inference utilities."""

from __future__ import annotations

import numpy as np
import pytest

from astrovox.distributed import DataParallel, DistributedConfig, ModelShard, PipelineStage, TensorParallel, gather_tensors, shard_tensor


def test_shard_tensor_single_rank_returns_original():
    tensor = np.ones((4, 3), dtype=np.float32)
    result = shard_tensor(tensor, world_size=1, rank=0)
    np.testing.assert_array_equal(result, tensor)


def test_shard_tensor_splits_first_dimension():
    tensor = np.ones((4, 3), dtype=np.float32)
    result = shard_tensor(tensor, world_size=2, rank=0)
    assert result.shape[0] == 2


def test_gather_tensors_concatenates():
    tensors = [np.ones((2, 3), dtype=np.float32), np.ones((2, 3), dtype=np.float32) * 2]
    result = gather_tensors(tensors, dim=0)
    assert result.shape == (4, 3)


def test_data_parallel_all_reduce_averages():
    config = DistributedConfig(world_size=2, rank=0)
    dp = DataParallel(config)
    gradients = [np.ones((2, 2), dtype=np.float32), np.ones((2, 2), dtype=np.float32) * 2]
    result = dp.all_reduce(gradients)
    np.testing.assert_allclose(result[0], np.ones((2, 2), dtype=np.float32) * 1.5)


def test_tensor_parallel_splits_weight():
    tp = TensorParallel(world_size=2, rank=0)
    weight = np.ones((4, 3), dtype=np.float32)
    shard = tp.split_weight(weight, axis=0)
    assert shard.shape[0] == 2
