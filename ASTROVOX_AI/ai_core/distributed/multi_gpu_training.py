from typing import Optional, Dict, Any, List
import torch
import torch.nn as nn
import torch.distributed as dist
from ASTROVOX_AI.ai_core.distributed.nccl import NCCLBackend


class MultiGPUTraining:
    def __init__(self, model: nn.Module, optimizer: torch.optim.Optimizer, device_ids: Optional[List[int]] = None, use_ddp: bool = True):
        self.device_ids = device_ids or list(range(torch.cuda.device_count()))
        self.num_gpus = len(self.device_ids)
        self.use_ddp = use_ddp
        self.backend = NCCLBackend(self.num_gpus, self.device_ids)
        if use_ddp and self.num_gpus > 1:
            self.model = nn.parallel.DistributedDataParallel(model, device_ids=self.device_ids)
        else:
            self.model = model
        self.optimizer = optimizer
        self.model.to(f'cuda:{self.device_ids[0]}')

    def train_step(self, batch: Dict[str, torch.Tensor], loss_fn: callable) -> float:
        self.model.train()
        input_ids = batch['input_ids'].to(f'cuda:{self.device_ids[0]}')
        labels = batch.get('labels', input_ids).to(f'cuda:{self.device_ids[0]}')
        logits = self.model(input_ids)
        loss = loss_fn(logits.view(-1, logits.size(-1)), labels.view(-1))
        loss.backward()
        self.optimizer.step()
        self.optimizer.zero_grad()
        return loss.item()

    def cleanup(self) -> None:
        if self.use_ddp:
            dist.destroy_process_group()
        self.backend.cleanup()
