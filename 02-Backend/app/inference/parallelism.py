"""Tensor parallelism and pipeline parallelism implementations."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.distributed as dist

logger = logging.getLogger(__name__)


class ParallelismStrategy(str, Enum):
    TENSOR = "tensor"
    PIPELINE = "pipeline"
    HYBRID = "hybrid"
    NONE = "none"


@dataclass
class ParallelConfig:
    strategy: ParallelismStrategy = ParallelismStrategy.NONE
    world_size: int = 1
    rank: int = 0
    tp_size: int = 1
    pp_size: int = 1
    dp_size: int = 1
    micro_batch_size: int = 1
    gradient_accumulation_steps: int = 1


class TensorParallelism:
    def __init__(self, config: ParallelConfig):
        self.config = config
        self.tp_size = config.tp_size
        self.rank = config.rank
        self.world_size = config.world_size

    def shard_linear(self, linear: nn.Linear, dim: int = 0) -> nn.Linear:
        in_features = linear.in_features
        out_features = linear.out_features
        if dim == 0:
            assert out_features % self.tp_size == 0, "Output features must be divisible by TP size"
            shard_out = out_features // self.tp_size
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
            assert in_features % self.tp_size == 0, "Input features must be divisible by TP size"
            shard_in = in_features // self.tp_size
            start = self.rank * shard_in
            end = start + shard_in
            weight_shard = linear.weight.data[:, start:end].clone()
            sharded = nn.Linear(shard_in, out_features, bias=False)
            sharded.weight.data.copy_(weight_shard)
            return sharded
        raise ValueError(f"Unsupported shard dim: {dim}")

    def shard_embedding(self, embedding: nn.Embedding) -> nn.Embedding:
        assert embedding.embedding_dim % self.tp_size == 0, "Embedding dim must be divisible by TP size"
        shard_dim = embedding.embedding_dim // self.tp_size
        start = self.rank * shard_dim
        end = start + shard_dim
        weight_shard = embedding.weight.data[:, start:end].clone()
        sharded = nn.Embedding(embedding.num_embeddings, shard_dim)
        sharded.weight.data.copy_(weight_shard)
        return sharded

    def all_reduce(self, tensor: torch.Tensor) -> torch.Tensor:
        if self.tp_size <= 1:
            return tensor
        dist.all_reduce(tensor, op=dist.ReduceOp.SUM)
        return tensor

    def all_gather(self, tensor: torch.Tensor, dim: int = 0) -> torch.Tensor:
        if self.tp_size <= 1:
            return tensor
        shape = list(tensor.shape)
        shape[dim] *= self.tp_size
        gathered = torch.empty(shape, device=tensor.device, dtype=tensor.dtype)
        tensor_list = [torch.empty_like(tensor) for _ in range(self.tp_size)]
        dist.all_gather(tensor_list, tensor)
        torch.cat(tensor_list, dim=dim, out=gathered)
        return gathered

    def reduce_scatter(self, tensor: torch.Tensor, dim: int = 0) -> torch.Tensor:
        if self.tp_size <= 1:
            return tensor
        shard_size = tensor.shape[dim] // self.tp_size
        shard = tensor.split(shard_size, dim=dim)[self.rank]
        output = torch.empty_like(shard)
        dist.reduce_scatter(output, [torch.empty_like(shard) for _ in range(self.tp_size)], op=dist.ReduceOp.SUM)
        return output

    def forward_linear(self, linear: nn.Linear, x: torch.Tensor, dim: int = 0) -> torch.Tensor:
        local_out = linear(x)
        return self.all_reduce(local_out)


class PipelineParallelism:
    def __init__(self, config: ParallelConfig):
        self.config = config
        self.pp_size = config.pp_size
        self.rank = config.rank
        self.micro_batch_size = config.micro_batch_size
        self.stages: List[nn.Module] = []
        self._stage_outputs: List[torch.Tensor] = []
        self._send_buffer: Optional[torch.Tensor] = None
        self._recv_buffer: Optional[torch.Tensor] = None

    def partition(self, model: nn.Module, num_stages: int) -> List[nn.Module]:
        modules = list(model.children())
        stage_size = max(1, len(modules) // num_stages)
        stages = []
        for i in range(0, len(modules), stage_size):
            stage = nn.Sequential(*modules[i:i + stage_size])
            stages.append(stage)
        self.stages = stages
        logger.info("Partitioned model into %d stages", len(stages))
        return stages

    def forward_stage(self, stage_idx: int, x: torch.Tensor) -> torch.Tensor:
        if stage_idx >= len(self.stages):
            raise ValueError(f"Stage {stage_idx} does not exist")
        return self.stages[stage_idx](x)

    def backward_stage(self, stage_idx: int, grad_output: torch.Tensor) -> torch.Tensor:
        if stage_idx >= len(self.stages):
            raise ValueError(f"Stage {stage_idx} does not exist")
        stage = self.stages[stage_idx]
        for param in stage.parameters():
            if param.grad is not None:
                param.grad = param.grad + grad_output
        return grad_output

    def schedule_1f1b(self, num_micro_batches: int) -> List[Tuple[int, str]]:
        schedule = []
        for mb in range(num_micro_batches):
            if self.rank < self.pp_size - 1:
                schedule.append((mb, "forward"))
            if self.rank > 0:
                schedule.append((mb, "backward"))
        return schedule

    def initialize_buffers(self, shape: Tuple[int, int], device: torch.device, dtype: torch.dtype) -> None:
        self._send_buffer = torch.empty(shape, device=device, dtype=dtype)
        self._recv_buffer = torch.empty(shape, device=device, dtype=dtype)

    def send(self, tensor: torch.Tensor, dest_rank: int) -> None:
        if self._send_buffer is None:
            self._send_buffer = tensor.clone()
        else:
            self._send_buffer.copy_(tensor)
        dist.send(self._send_buffer, dst=dest_rank)

    def recv(self, src_rank: int) -> torch.Tensor:
        if self._recv_buffer is None:
            self._recv_buffer = torch.empty_like(self._send_buffer)
        dist.recv(self._recv_buffer, src=src_rank)
        return self._recv_buffer.clone()
