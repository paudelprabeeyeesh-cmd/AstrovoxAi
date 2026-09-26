"""Data parallelism: DDP, batch splitting, gradient synchronization."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import torch
import torch.nn as nn
import torch.distributed as dist

logger = logging.getLogger(__name__)


@dataclass
class DataParallelConfig:
    world_size: int = 1
    rank: int = 0
    backend: str = "nccl"
    find_unused_parameters: bool = False
    bucket_cap_mb: int = 25
    gradient_as_bucket_view: bool = True


class DataParallelism:
    def __init__(self, model: nn.Module, config: DataParallelConfig,
                 device_ids: Optional[List[int]] = None):
        self.config = config
        self.rank = config.rank
        self.world_size = config.world_size
        self.device_ids = device_ids or (
            [0] if torch.cuda.device_count() == 0
            else list(range(torch.cuda.device_count()))
        )
        if self.world_size > 1:
            self.model = nn.parallel.DistributedDataParallel(
                model,
                device_ids=self.device_ids,
                find_unused_parameters=config.find_unused_parameters,
                bucket_cap_mb=config.bucket_cap_mb,
                gradient_as_bucket_view=config.gradient_as_bucket_view,
            )
        else:
            self.model = model

    def train_step(self, batch: Dict[str, torch.Tensor],
                   loss_fn: Any) -> float:
        self.model.train()
        device = next(self.model.parameters()).device
        input_ids = batch["input_ids"].to(device)
        labels = batch.get("labels", input_ids).to(device)
        logits = self.model(input_ids)
        loss = loss_fn(logits.view(-1, logits.size(-1)), labels.view(-1))
        self.model.zero_grad()
        loss.backward()
        for param in self.model.parameters():
            if param.grad is not None:
                dist.all_reduce(param.grad, op=dist.ReduceOp.SUM)
                param.grad /= self.world_size
        return loss.item()

    def broadcast_parameters(self, model: nn.Module, src: int = 0) -> None:
        for param in model.parameters():
            dist.broadcast(param.data, src=src)

    def all_reduce_gradients(self, model: nn.Module) -> None:
        for param in model.parameters():
            if param.grad is not None:
                dist.all_reduce(param.grad, op=dist.ReduceOp.SUM)

    def barrier(self) -> None:
        dist.barrier()

    def cleanup(self) -> None:
        if self.world_size > 1:
            dist.destroy_process_group()
