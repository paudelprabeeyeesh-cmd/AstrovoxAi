"""Tensor parallelism service wrapper for distributed inference."""

from __future__ import annotations

import logging
from typing import Optional

import torch
import torch.nn as nn

from ASTROVOX_AI.ai_core.inference.tensor_parallelism import TensorParallelism, TensorParallelConfig

logger = logging.getLogger(__name__)


class TensorParallelService:
    def __init__(self, world_size: int = 1, rank: int = 0, shard_dim: int = 0):
        self.config = TensorParallelConfig(world_size=world_size, rank=rank, shard_dim=shard_dim)
        self.tp = TensorParallelism(self.config)

    def shard_linear(self, linear: nn.Linear, dim: int = 0) -> nn.Linear:
        return self.tp.shard_linear(linear, dim=dim)

    def shard_embedding(self, embedding: nn.Embedding) -> nn.Embedding:
        return self.tp.shard_embedding(embedding)

    def forward_linear(self, linear: nn.Linear, x: torch.Tensor, dim: int = 0) -> torch.Tensor:
        return self.tp.forward_linear(linear, x, dim=dim)

    def all_reduce(self, tensor: torch.Tensor) -> torch.Tensor:
        return self.tp.all_reduce(tensor)

    def all_gather(self, tensor: torch.Tensor, dim: int = 0) -> torch.Tensor:
        return self.tp.all_gather(tensor, dim=dim)
