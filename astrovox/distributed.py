"""Distributed training and inference utilities.

Provides lightweight wrappers for data parallelism, model sharding, and
basic cluster coordination. These are designed to be optional and
incremental: the single-node path is unchanged, and distributed features
are activated only when explicitly configured.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Iterator, List, Optional, Tuple


@dataclass(frozen=True)
class DistributedConfig:
    world_size: int = 1
    rank: int = 0
    backend: str = "cpu"
    master_addr: str = "127.0.0.1"
    master_port: int = 29500


class DataParallel:
    """Simple data-parallel gradient aggregation across replicas."""

    def __init__(self, config: DistributedConfig) -> None:
        self.config = config

    def all_reduce(self, gradients: List[np.ndarray]) -> List[np.ndarray]:
        if self.config.world_size <= 1:
            return gradients
        return [np.sum(gradients, axis=0) / self.config.world_size for grad in gradients]


def shard_tensor(tensor: np.ndarray, world_size: int, rank: int, dim: int = 0) -> np.ndarray:
    if world_size <= 1:
        return tensor
    size = tensor.shape[dim]
    start = math.floor(size * rank / world_size)
    end = math.floor(size * (rank + 1) / world_size)
    slices = [slice(None)] * tensor.ndim
    slices[dim] = slice(start, end)
    return tensor[tuple(slices)]


def gather_tensors(tensors: List[np.ndarray], dim: int = 0) -> np.ndarray:
    if len(tensors) == 1:
        return tensors[0]
    return np.concatenate(tensors, axis=dim)


@dataclass(frozen=True)
class ShardMetadata:
    rank: int
    dim: int
    start: int
    end: int
    shape: Tuple[int, ...]


class ModelShard:
    """Partial model state for a single rank."""

    def __init__(self, rank: int, shards: List[ShardMetadata]) -> None:
        self.rank = rank
        self.shards = shards

    def local_shard(self, tensor: np.ndarray, dim: int = 0) -> np.ndarray:
        meta = next((s for s in self.shards if s.rank == self.rank), None)
        if meta is None:
            raise ValueError("No shard metadata for rank")
        slices = [slice(None)] * tensor.ndim
        slices[dim] = slice(meta.start, meta.end)
        return tensor[tuple(slices)]


class PipelineStage:
    """A sequential stage in a pipeline-parallel model."""

    def __init__(self, modules: List[Any]) -> None:
        self.modules = modules

    def forward(self, x: np.ndarray) -> np.ndarray:
        for module in self.modules:
            x = module(x)
        return x


class TensorParallel:
    """Column-wise tensor parallelism splitter."""

    def __init__(self, world_size: int, rank: int) -> None:
        self.world_size = max(1, world_size)
        self.rank = max(0, rank)

    def split_weight(self, weight: np.ndarray, axis: int = 0) -> np.ndarray:
        if self.world_size <= 1:
            return weight
        size = weight.shape[axis]
        start = math.floor(size * self.rank / self.world_size)
        end = math.floor(size * (self.rank + 1) / self.world_size)
        slices = [slice(None)] * weight.ndim
        slices[axis] = slice(start, end)
        return weight[tuple(slices)]

    def gather_gradients(self, gradients: List[np.ndarray], axis: int = 0) -> np.ndarray:
        return gather_tensors(gradients, dim=axis)
