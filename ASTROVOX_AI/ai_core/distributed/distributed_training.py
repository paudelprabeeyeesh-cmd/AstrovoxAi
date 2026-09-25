from typing import Optional, Dict, Any, List
import torch
import torch.nn as nn
import torch.distributed as dist
from ASTROVOX_AI.ai_core.distributed.nccl import NCCLBackend


class DistributedTraining:
    def __init__(self, model: nn.Module, optimizer: torch.optim.Optimizer, world_size: int, rank: int, backend: str = 'nccl', device_ids: Optional[List[int]] = None):
        self.model = model
        self.optimizer = optimizer
        self.world_size = world_size
        self.rank = rank
        self.backend = NCCLBackend(world_size, device_ids)
        self.backend.init_process_group(rank)
        self.model = nn.parallel.DistributedDataParallel(model, device_ids=device_ids)

    def train_step(self, batch: Dict[str, torch.Tensor], loss_fn: callable) -> float:
        self.model.train()
        input_ids = batch['input_ids'].cuda()
        labels = batch.get('labels', input_ids).cuda()
        logits = self.model(input_ids)
        loss = loss_fn(logits.view(-1, logits.size(-1)), labels.view(-1))
        loss.backward()
        self.optimizer.step()
        self.optimizer.zero_grad()
        return loss.item()

    def save_checkpoint(self, path: str) -> None:
        torch.save({'model': self.model.state_dict(), 'optimizer': self.optimizer.state_dict(), 'rank': self.rank}, path)

    def cleanup(self) -> None:
        self.backend.cleanup()
