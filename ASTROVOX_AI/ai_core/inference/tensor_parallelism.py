"""Tensor parallelism for ASTROVOX_AI inference core."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.distributed as dist

logger = logging.getLogger(__name__)


@dataclass
class TensorParallelConfig:
    world_size: int = 1
    rank: int = 0
    shard_dim: int = 0


class TensorParallelism:
    def __init__(self, config: TensorParallelConfig):
        self.config = config
        self.world_size = config.world_size
        self.rank = config.rank
        self.shard_dim = config.shard_dim

    def shard_linear(self, linear: nn.Linear, dim: int = 0) -> nn.Linear:
        in_features = linear.in_features
        out_features = linear.out_features
        if dim == 0:
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
        if dim == 1:
            assert in_features % self.world_size == 0, "Input features must be divisible by TP size"
            shard_in = in_features // self.world_size
            start = self.rank * shard_in
            end = start + shard_in
            weight_shard = linear.weight.data[:, start:end].clone()
            sharded = nn.Linear(shard_in, out_features, bias=False)
            sharded.weight.data.copy_(weight_shard)
            return sharded
        raise ValueError(f"Unsupported shard dim: {dim}")

    def shard_embedding(self, embedding: nn.Embedding) -> nn.Embedding:
        assert embedding.embedding_dim % self.world_size == 0, "Embedding dim must be divisible by TP size"
        shard_dim = embedding.embedding_dim // self.world_size
        start = self.rank * shard_dim
        end = start + shard_dim
        weight_shard = embedding.weight.data[:, start:end].clone()
        sharded = nn.Embedding(embedding.num_embeddings, shard_dim)
        sharded.weight.data.copy_(weight_shard)
        return sharded

    def all_reduce(self, tensor: torch.Tensor) -> torch.Tensor:
        if self.world_size <= 1:
            return tensor
        dist.all_reduce(tensor, op=dist.ReduceOp.SUM)
        return tensor

    def all_gather(self, tensor: torch.Tensor, dim: int = 0) -> torch.Tensor:
        if self.world_size <= 1:
            return tensor
        shape = list(tensor.shape)
        shape[dim] *= self.world_size
        gathered = torch.empty(shape, device=tensor.device, dtype=tensor.dtype)
        tensor_list = [torch.empty_like(tensor) for _ in range(self.world_size)]
        dist.all_gather(tensor_list, tensor)
        torch.cat(tensor_list, dim=dim, out=gathered)
        return gathered

    def reduce_scatter(self, tensor: torch.Tensor, dim: int = 0) -> torch.Tensor:
        if self.world_size <= 1:
            return tensor
        shard_size = tensor.shape[dim] // self.world_size
        shard = tensor.split(shard_size, dim=dim)[self.rank]
        output = torch.empty_like(shard)
        dist.reduce_scatter(output, [torch.empty_like(shard) for _ in range(self.world_size)], op=dist.ReduceOp.SUM)
        return output

    def forward_linear(self, linear: nn.Linear, x: torch.Tensor, dim: int = 0) -> torch.Tensor:
        local_out = linear(x)
        return self.all_reduce(local_out)
