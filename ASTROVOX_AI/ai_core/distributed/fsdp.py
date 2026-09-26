"""FSDP: Fully Sharded Data Parallel with all-gather forward, reduce-scatter backward."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

import torch
import torch.nn as nn
import torch.distributed as dist

logger = logging.getLogger(__name__)


@dataclass
class FSDPConfig:
    world_size: int = 1
    rank: int = 0
    sharding_strategy: str = "FULL_SHARD"
    auto_wrap_policy: Optional[str] = None
    cpu_offload: bool = False
    mixed_precision: bool = False
    backward_prefetch: bool = True
    forward_prefetch: bool = True


class _FSDPWrapper(nn.Module):
    def __init__(self, module: nn.Module, config: FSDPConfig, rank: int, world_size: int):
        super().__init__()
        self.config = config
        self.rank = rank
        self.world_size = world_size
        self._sharded_module = module
        self._param_names: List[str] = [n for n, _ in module.named_parameters() if _.requires_grad]
        self._local_param_shards: Dict[str, torch.Tensor] = {}
        self._gathered: bool = False

    def _gather_params(self) -> None:
        if self._gathered:
            return
        for name, param in self._sharded_module.named_parameters(recurse=False):
            if not param.requires_grad:
                continue
            flat = param.data.view(-1)
            shard_size = flat.numel() // self.world_size
            local_shard = flat[self.rank * shard_size:(self.rank + 1) * shard_size].clone()
            gathered_list = [torch.zeros_like(local_shard) for _ in range(self.world_size)]
            dist.all_gather(gathered_list, local_shard)
            full = torch.cat(gathered_list)
            param.data.copy_(full.view_as(param.data))
        self._gathered = True

    def _shard_params(self) -> None:
        if not self._gathered:
            return
        for name, param in self._sharded_module.named_parameters(recurse=False):
            if not param.requires_grad:
                continue
            flat = param.data.view(-1)
            shard_size = flat.numel() // self.world_size
            local_shard = flat[self.rank * shard_size:(self.rank + 1) * shard_size].clone()
            param.data.zero_()
            param.data.view(-1)[self.rank * shard_size:(self.rank + 1) * shard_size] = local_shard
        self._gathered = False

    def forward(self, *args: Any, **kwargs: Any) -> Any:
        self._gather_params()
        out = self._sharded_module(*args, **kwargs)
        return out

    def backward(self, grad_output: Any) -> None:
        for name, param in self._sharded_module.named_parameters(recurse=False):
            if param.grad is not None:
                dist.reduce_scatter(param.grad, [torch.zeros_like(param.grad) for _ in range(self.world_size)], op=dist.ReduceOp.SUM)
        self._shard_params()


class FSDP:
    def __init__(self, model: nn.Module, config: FSDPConfig):
        self.config = config
        self.world_size = config.world_size
        self.rank = config.rank
        self.wrapper = _FSDPWrapper(model, config, config.rank, config.world_size)

    def forward(self, *args: Any, **kwargs: Any) -> Any:
        return self.wrapper(*args, **kwargs)

    def backward(self, loss: torch.Tensor) -> None:
        loss.backward()
        self.wrapper._shard_params()

    def state_dict(self) -> Dict[str, Any]:
        full_state: Dict[str, Any] = {}
        for name, param in self.wrapper._sharded_module.named_parameters():
            if param.requires_grad:
                local = param.data.view(-1)
                shard_size = local.numel() // self.world_size
                local_shard = local[self.rank * shard_size:(self.rank + 1) * shard_size].clone()
                gathered_list = [torch.zeros_like(local_shard) for _ in range(self.world_size)]
                dist.all_gather(gathered_list, local_shard)
                full_state[name] = torch.cat(gathered_list).view_as(param.data)
        return full_state

    def load_state_dict(self, state_dict: Dict[str, Any]) -> None:
        for name, param in self.wrapper._sharded_module.named_parameters():
            if name in state_dict and param.requires_grad:
                full = state_dict[name]
                flat = full.view(-1)
                shard_size = flat.numel() // self.world_size
                param.data.zero_()
                param.data.view(-1)[self.rank * shard_size:(self.rank + 1) * shard_size] = flat[self.rank * shard_size:(self.rank + 1) * shard_size]

    def train_step(self, batch: Dict[str, torch.Tensor], loss_fn: Any, optimizer: torch.optim.Optimizer) -> float:
        self.wrapper.train()
        input_ids = batch["input_ids"].to(next(self.wrapper.parameters()).device)
        labels = batch.get("labels", input_ids).to(input_ids.device)
        logits = self.forward(input_ids)
        loss = loss_fn(logits.view(-1, logits.size(-1)), labels.view(-1))
        self.backward(loss)
        optimizer.step()
        return loss.item()
