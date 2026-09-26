"""Model sharding and tensor parallelism utilities."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


class ShardingStrategy(str, Enum):
    TENSOR_PARALLEL = "tensor_parallel"
    PIPELINE_PARALLEL = "pipeline_parallel"
    HYBRID = "hybrid"
    NONE = "none"


@dataclass
class ShardConfig:
    strategy: ShardingStrategy = ShardingStrategy.TENSOR_PARALLEL
    world_size: int = 1
    rank: int = 0
    shard_dim: int = 0
    pipeline_stages: int = 1
    stage_idx: int = 0


class TensorParallelSharder:
    def __init__(self, config: ShardConfig):
        self.config = config

    def shard_linear(self, linear: nn.Linear) -> nn.Module:
        world_size = self.config.world_size
        rank = self.config.rank
        shard_dim = self.config.shard_dim
        in_features = linear.in_features
        out_features = linear.out_features
        if shard_dim == 0:
            assert out_features % world_size == 0, "Output features must be divisible by world_size"
            shard_out = out_features // world_size
            weight_shard = linear.weight.data[rank * shard_out:(rank + 1) * shard_out, :].clone()
            bias_shard = linear.bias.data[rank * shard_out:(rank + 1) * shard_out].clone() if linear.bias is not None else None
            sharded = nn.Linear(in_features, shard_out, bias=linear.bias is not None)
            sharded.weight.data.copy_(weight_shard)
            if bias_shard is not None:
                sharded.bias.data.copy_(bias_shard)
            return sharded
        if shard_dim == 1:
            assert in_features % world_size == 0, "Input features must be divisible by world_size"
            shard_in = in_features // world_size
            weight_shard = linear.weight.data[:, rank * shard_in:(rank + 1) * shard_in].clone()
            sharded = nn.Linear(shard_in, out_features, bias=False)
            sharded.weight.data.copy_(weight_shard)
            return sharded
        raise ValueError(f"Unsupported shard_dim: {shard_dim}")

    def shard_embedding(self, embedding: nn.Embedding) -> nn.Module:
        world_size = self.config.world_size
        rank = self.config.rank
        num_embeddings = embedding.num_embeddings
        embedding_dim = embedding.embedding_dim
        assert embedding_dim % world_size == 0, "Embedding dim must be divisible by world_size"
        shard_dim = embedding_dim // world_size
        weight_shard = embedding.weight.data[:, rank * shard_dim:(rank + 1) * shard_dim].clone()
        sharded = nn.Embedding(num_embeddings, shard_dim)
        sharded.weight.data.copy_(weight_shard)
        return sharded

    def all_gather(self, tensor: torch.Tensor) -> torch.Tensor:
        if self.config.world_size <= 1:
            return tensor
        gathered = [torch.empty_like(tensor) for _ in range(self.config.world_size)]
        torch.distributed.all_gather(gathered, tensor)
        return torch.cat(gathered, dim=self.config.shard_dim)

    def reduce_scatter(self, tensor: torch.Tensor) -> torch.Tensor:
        if self.config.world_size <= 1:
            return tensor
        shard_size = tensor.shape[self.config.shard_dim] // self.config.world_size
        shard = tensor.split(shard_size, dim=self.config.shard_dim)[self.config.rank]
        torch.distributed.reduce_scatter_output = shard
        torch.distributed.reduce_scatter(shard, [torch.empty_like(shard) for _ in range(self.config.world_size)])
        return shard


class ModelSharder:
    def __init__(self, config: ShardConfig):
        self.config = config
        self._tp_sharder = TensorParallelSharder(config)

    def shard_model(self, model: nn.Module) -> nn.Module:
        if self.config.strategy == ShardingStrategy.TENSOR_PARALLEL:
            return self._shard_tensor_parallel(model)
        if self.config.strategy == ShardingStrategy.NONE:
            return model
        raise NotImplementedError(f"Sharding strategy {self.config.strategy} not implemented")

    def _shard_tensor_parallel(self, model: nn.Module) -> nn.Module:
        for name, module in model.named_modules():
            if isinstance(module, nn.Linear):
                sharded = self._tp_sharder.shard_linear(module)
                parent = self._get_parent(model, name)
                if parent is not None:
                    attr = name.split(".")[-1]
                    setattr(parent, attr, sharded)
            elif isinstance(module, nn.Embedding):
                sharded = self._tp_sharder.shard_embedding(module)
                parent = self._get_parent(model, name)
                if parent is not None:
                    attr = name.split(".")[-1]
                    setattr(parent, attr, sharded)
        return model

    @staticmethod
    def _get_parent(model: nn.Module, name: str) -> Optional[nn.Module]:
        parts = name.split(".")
        if len(parts) == 1:
            return model
        parent_name = ".".join(parts[:-1])
        for n, m in model.named_modules():
            if n == parent_name:
                return m
        return None


def get_shard_config_from_env() -> ShardConfig:
    return ShardConfig(
        strategy=ShardingStrategy(os.getenv("SHARDING_STRATEGY", "tensor_parallel")),
        world_size=int(os.getenv("WORLD_SIZE", "1")),
        rank=int(os.getenv("RANK", "0")),
        shard_dim=int(os.getenv("SHARD_DIM", "0")),
        pipeline_stages=int(os.getenv("PIPELINE_STAGES", "1")),
        stage_idx=int(os.getenv("STAGE_IDX", "0")),
    )
