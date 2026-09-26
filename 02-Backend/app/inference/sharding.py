"""Model sharding with ZeRO and hybrid sharding strategies."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


class ShardingStrategy(str, Enum):
    TENSOR_PARALLEL = "tensor_parallel"
    PIPELINE_PARALLEL = "pipeline_parallel"
    ZERO_STAGE_1 = "zero_stage_1"
    ZERO_STAGE_2 = "zero_stage_2"
    ZERO_STAGE_3 = "zero_stage_3"
    HYBRID = "hybrid"
    NONE = "none"


@dataclass
class ShardConfig:
    strategy: ShardingStrategy = ShardingStrategy.NONE
    world_size: int = 1
    rank: int = 0
    shard_dim: int = 0
    pipeline_stages: int = 1
    stage_idx: int = 0
    zero_stage: int = 1


class ZeROSharding:
    def __init__(self, config: ShardConfig):
        self.config = config
        self.world_size = config.world_size
        self.rank = config.rank
        self.stage = config.zero_stage
        self._partitioned_params: Dict[str, torch.Tensor] = {}

    def partition_optimizer_state(self, param_name: str, param: torch.Tensor) -> torch.Tensor:
        if self.stage >= 1:
            shard = self._get_shard(param, self.config.shard_dim)
            self._partitioned_params[param_name] = shard
            return shard
        return param

    def partition_gradients(self, param_name: str, grad: torch.Tensor) -> torch.Tensor:
        if self.stage >= 2:
            return self._get_shard(grad, self.config.shard_dim)
        return grad

    def partition_parameters(self, param_name: str, param: torch.Tensor) -> torch.Tensor:
        if self.stage >= 3:
            shard = self._get_shard(param, self.config.shard_dim)
            self._partitioned_params[param_name] = shard
            return shard
        return param

    def _get_shard(self, tensor: torch.Tensor, dim: int) -> torch.Tensor:
        shard_size = tensor.shape[dim] // self.world_size
        start = self.rank * shard_size
        end = start + shard_size
        return tensor.split(shard_size, dim=dim)[self.rank]

    def all_gather_gradients(self, grad: torch.Tensor, dim: int = 0) -> torch.Tensor:
        if self.world_size <= 1:
            return grad
        gathered = [torch.empty_like(grad) for _ in range(self.world_size)]
        torch.distributed.all_gather(gathered, grad)
        return torch.cat(gathered, dim=dim)

    def reduce_scatter_gradients(self, grad: torch.Tensor, dim: int = 0) -> torch.Tensor:
        if self.world_size <= 1:
            return grad
        shard_size = grad.shape[dim] // self.world_size
        shard = grad.split(shard_size, dim=dim)[self.rank]
        output = torch.empty_like(shard)
        torch.distributed.reduce_scatter(output, [torch.empty_like(shard) for _ in range(self.world_size)], op=torch.distributed.ReduceOp.SUM)
        return output

    def get_sharding_plan(self, model: nn.Module) -> Dict[str, Any]:
        plan = {}
        for name, param in model.named_parameters():
            if self.stage >= 3:
                plan[name] = {"shard": True, "dim": self.config.shard_dim, "size": param.shape[self.config.shard_dim] // self.world_size}
            elif self.stage >= 2:
                plan[name] = {"grad_shard": True, "dim": self.config.shard_dim}
            elif self.stage >= 1:
                plan[name] = {"optimizer_shard": True, "dim": self.config.shard_dim}
            else:
                plan[name] = {"shard": False}
        return plan


class HybridSharding:
    def __init__(self, config: ShardConfig):
        self.config = config
        self.tp = TensorParallelSharding(config)
        self.zero = ZeROSharding(config)

    def shard_model(self, model: nn.Module) -> nn.Module:
        if self.config.strategy == ShardingStrategy.HYBRID:
            model = self.tp.shard_model(model)
            if self.config.zero_stage > 0:
                self.zero.apply_sharding(model)
            return model
        if self.config.strategy == ShardingStrategy.TENSOR_PARALLEL:
            return self.tp.shard_model(model)
        if self.config.strategy in (ShardingStrategy.ZERO_STAGE_1, ShardingStrategy.ZERO_STAGE_2, ShardingStrategy.ZERO_STAGE_3):
            self.zero.apply_sharding(model)
            return model
        return model


class TensorParallelSharding:
    def __init__(self, config: ShardConfig):
        self.config = config
        self.world_size = config.world_size
        self.rank = config.rank
        self.shard_dim = config.shard_dim

    def shard_model(self, model: nn.Module) -> nn.Module:
        for name, module in model.named_modules():
            if isinstance(module, nn.Linear):
                sharded = self._shard_linear(module)
                parent = self._get_parent(model, name)
                if parent is not None:
                    setattr(parent, name.split(".")[-1], sharded)
            elif isinstance(module, nn.Embedding):
                sharded = self._shard_embedding(module)
                parent = self._get_parent(model, name)
                if parent is not None:
                    setattr(parent, name.split(".")[-1], sharded)
        return model

    def _shard_linear(self, linear: nn.Linear) -> nn.Linear:
        in_features = linear.in_features
        out_features = linear.out_features
        if self.shard_dim == 0:
            assert out_features % self.world_size == 0, "Output features must be divisible by TP size"
            shard_out = out_features // self.world_size
            start = self.rank * shard_out
            end = start + shard_out
            weight_shard = linear.weight.data[start:end, :].clone()
            bias_shard = linear.bias.data[start:end].clone() if linear.bias is not None else None
            sharded = nn.Linear(in_features, shard_out, bias=linear.bias is not None)
            sharded.weight.data.copy_(weight_shard)
            if bias_shard is not None:
                sharded.bias.data.copy_(bias_shard)
            return sharded
        if self.shard_dim == 1:
            assert in_features % self.world_size == 0, "Input features must be divisible by TP size"
            shard_in = in_features // self.world_size
            start = self.rank * shard_in
            end = start + shard_in
            weight_shard = linear.weight.data[:, start:end].clone()
            sharded = nn.Linear(shard_in, out_features, bias=False)
            sharded.weight.data.copy_(weight_shard)
            return sharded
        raise ValueError(f"Unsupported shard_dim: {self.shard_dim}")

    def _shard_embedding(self, embedding: nn.Embedding) -> nn.Embedding:
        assert embedding.embedding_dim % self.world_size == 0, "Embedding dim must be divisible by TP size"
        shard_dim = embedding.embedding_dim // self.world_size
        start = self.rank * shard_dim
        end = start + shard_dim
        weight_shard = embedding.weight.data[:, start:end].clone()
        sharded = nn.Embedding(embedding.num_embeddings, shard_dim)
        sharded.weight.data.copy_(weight_shard)
        return sharded

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
