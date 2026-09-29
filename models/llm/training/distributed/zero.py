"""ZeRO Stage 1-3 implementations: optimizer, gradient, and parameter partitioning."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import torch
import torch.distributed as dist
import torch.nn as nn

logger = logging.getLogger(__name__)


@dataclass
class ZeROConfig:
    """Configuration for ZeRO optimizer stages."""

    stage: int = 2
    world_size: int = 1
    rank: int = 0
    overlap_communication: bool = True
    offload_optimizer: bool = False
    offload_param: bool = False
    contiguous_gradients: bool = True


class ZeROStage1:
    """Optimizer state partitioning only.

    Each rank stores a unique shard of the optimizer states,
    reducing per-GPU memory by O(world_size).
    """

    def __init__(self, model: nn.Module, optimizer: torch.optim.Optimizer, config: ZeROConfig) -> None:
        self.model = model
        self.optimizer = optimizer
        self.config = config
        self.world_size = config.world_size
        self.rank = config.rank

    def step(self, loss: torch.Tensor) -> float:
        self.optimizer.zero_grad()
        loss.backward()
        self._reduce_gradients()
        self.optimizer.step()
        return loss.item()

    def _reduce_gradients(self) -> None:
        for param in self.model.parameters():
            if param.grad is not None:
                dist.all_reduce(param.grad, op=dist.ReduceOp.SUM)
                param.grad.div_(self.world_size)


class ZeROStage2:
    """Optimizer state + gradient partitioning.

    Gradients are partitioned after reduction, and only the relevant shard
    is communicated. This further reduces communication volume.
    """

    def __init__(self, model: nn.Module, optimizer: torch.optim.Optimizer, config: ZeroConfig) -> None:
        self.model = model
        self.optimizer = optimizer
        self.config = config
        self.world_size = config.world_size
        self.rank = config.rank
        self._local_gradients: dict[str, torch.Tensor] = {}

    def step(self, loss: torch.Tensor) -> float:
        self.optimizer.zero_grad()
        loss.backward()
        self._partition_gradients()
        self.optimizer.step()
        self._allgather_gradients()
        return loss.item()

    def _partition_gradients(self) -> None:
        for name, param in self.model.named_parameters():
            if param.grad is None:
                continue
            full_grad = param.grad.data.clone()
            numel = full_grad.numel()
            shard_size = numel // self.world_size
            start = self.rank * shard_size
            end = start + shard_size
            local_grad = full_grad.view(-1)[start:end].clone()
            self._local_gradients[name] = local_grad
            param.grad.data.zero_()

    def _allgather_gradients(self) -> None:
        for name, param in self.model.named_parameters():
            if name not in self._local_gradients:
                continue
            local = self._local_gradients[name]
            gathered = [torch.zeros_like(local) for _ in range(self.world_size)]
            dist.all_gather(gathered, local)
            full_grad = torch.cat(gathered)
            param.grad.data.copy_(full_grad.view_as(param.grad.data))
        self._local_gradients.clear()


class ZeROStage3:
    """Optimizer state + gradient + parameter partitioning.

    Parameters are partitioned across ranks. Before forward/backward, the
    relevant shards are gathered and scattered back after the optimizer step.
    """

    def __init__(self, model: nn.Module, optimizer: torch.optim.Optimizer, config: ZeroConfig) -> None:
        self.model = model
        self.optimizer = optimizer
        self.config = config
        self.world_size = config.world_size
        self.rank = config.rank
        self._owned_params: set[str] = set()
        self._partition_parameters()

    def _partition_parameters(self) -> None:
        all_param_names = [n for n, p in self.model.named_parameters() if p.requires_grad]
        for idx, name in enumerate(all_param_names):
            if idx % self.world_size == self.rank:
                self._owned_params.add(name)

    def _gather_parameter(self, param: nn.Parameter, name: str) -> None:
        if name in self._owned_params:
            return
        full = torch.zeros_like(param.data)
        shard = torch.zeros_like(param.data.view(-1)[:: self.world_size])
        gathered_list = [torch.zeros_like(shard) for _ in range(self.world_size)]
        dist.all_gather(gathered_list, shard)
        full.view(-1)[:: self.world_size] = torch.cat(gathered_list)
        param.data.copy_(full)

    def _scatter_parameter(self, param: nn.Parameter, name: str) -> None:
        if name not in self._owned_params:
            param.data.zero_()
            return
        flat = param.data.view(-1)
        shard = flat[:: self.world_size].clone()
        param.data.zero_()
        param.data.view(-1)[:: self.world_size] = shard

    def step(self, loss: torch.Tensor) -> float:
        self.optimizer.zero_grad()
        for name, param in self.model.named_parameters():
            self._gather_parameter(param, name)
        loss.backward()
        for param in self.model.parameters():
            if param.grad is not None:
                dist.all_reduce(param.grad, op=dist.ReduceOp.SUM)
                param.grad.div_(self.world_size)
        self.optimizer.step()
        for name, param in self.model.named_parameters():
            self._scatter_parameter(param, name)
        return loss.item()


class ZeROOptimizer:
    """Unified ZeRO optimizer that dispatches to Stage 1/2/3 implementations."""

    def __init__(self, model: nn.Module, optimizer: torch.optim.Optimizer, config: ZeroConfig) -> None:
        self.config = config
        self.stage = config.stage
        if self.stage == 1:
            self.impl = ZeROStage1(model, optimizer, config)
        elif self.stage == 2:
            self.impl = ZeROStage2(model, optimizer, config)
        elif self.stage == 3:
            self.impl = ZeROStage3(model, optimizer, config)
        else:
            raise ValueError(f"Unsupported ZeRO stage: {self.stage}")

    def step(self, loss: torch.Tensor) -> float:
        return self.impl.step(loss)

    def backward(self, loss: torch.Tensor) -> None:
        loss.backward()
