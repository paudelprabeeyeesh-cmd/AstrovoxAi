from typing import Optional, List
import torch
import torch.nn as nn
import torch.distributed as dist
from ASTROVOX_AI.ai_core.distributed.zero_optimizer import ZeroConfig, ZeROOptimizer


class DistributedOptimizer:
    def __init__(self, model: nn.Module, optimizer: torch.optim.Optimizer, world_size: int, rank: int, device_ids: Optional[List[int]] = None, zero_stage: int = 0):
        self.model = model
        self.optimizer = optimizer
        self.world_size = world_size
        self.rank = rank
        self.device_ids = device_ids
        self.zero_stage = zero_stage
        if zero_stage > 0:
            config = ZeroConfig(stage=zero_stage, world_size=world_size, rank=rank)
            self.zero_impl = ZeROOptimizer(model, optimizer, config)
        else:
            self.zero_impl = None

    def step(self, closure=None) -> None:
        for param in self.model.parameters():
            if param.grad is not None:
                dist.all_reduce(param.grad, op=dist.ReduceOp.SUM)
                param.grad /= self.world_size
        self.optimizer.step(closure)

    def zero_grad(self) -> None:
        self.optimizer.zero_grad()

    def zero_step(self, loss: torch.Tensor) -> float:
        if self.zero_impl is not None:
            return self.zero_impl.step(loss)
        raise ValueError("ZeRO not configured; pass zero_stage > 0")
