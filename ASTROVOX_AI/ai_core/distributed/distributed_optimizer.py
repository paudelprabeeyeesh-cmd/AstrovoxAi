from typing import Dict, Any, Optional, List
import torch
import torch.nn as nn
from ASTROVOX_AI.ai_core.distributed.nccl import NCCLBackend


class DistributedOptimizer:
    def __init__(self, model: nn.Module, optimizer: torch.optim.Optimizer, world_size: int, rank: int, device_ids: Optional[List[int]] = None):
        self.model = model
        self.optimizer = optimizer
        self.world_size = world_size
        self.rank = rank
        self.backend = NCCLBackend(world_size, device_ids)

    def step(self, closure=None) -> None:
        for param in self.model.parameters():
            if param.grad is not None:
                self.backend.all_reduce(param.grad)
                param.grad /= self.world_size
        self.optimizer.step(closure)

    def zero_grad(self) -> None:
        self.optimizer.zero_grad()
