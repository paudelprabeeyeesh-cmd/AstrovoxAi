from typing import Optional, List
import torch
import torch.nn as nn
from ASTROVOX_AI.ai_core.distributed.nccl import NCCLBackend


class CUDATensorParallelism:
    def __init__(self, model: nn.Module, tp_size: int = 2, device_ids: Optional[List[int]] = None):
        self.model = model
        self.tp_size = tp_size
        self.device_ids = device_ids or list(range(tp_size))
        self.backend = NCCLBackend(tp_size, self.device_ids)

    def shard_model(self) -> nn.Module:
        for name, module in self.model.named_modules():
            if isinstance(module, nn.Linear):
                out_features = module.out_features // self.tp_size
                shard = nn.Linear(module.in_features, out_features, bias=module.bias is not None)
                shard.weight.data = module.weight.data[:out_features, :].contiguous()
                if module.bias is not None:
                    shard.bias.data = module.bias.data[:out_features].contiguous()
                setattr(self.model, name, shard)
        return self.model

    def all_gather(self, tensor: torch.Tensor, dim: int = 0) -> torch.Tensor:
        gathered = [torch.zeros_like(tensor) for _ in range(self.tp_size)]
        self.backend.all_gather(gathered, tensor)
        return torch.cat(gathered, dim=dim)

    def all_reduce(self, tensor: torch.Tensor) -> torch.Tensor:
        self.backend.all_reduce(tensor)
        return tensor

    def forward_step(self, x: torch.Tensor) -> torch.Tensor:
        local_out = self.model(x)
        return self.all_gather(local_out, dim=-1)
