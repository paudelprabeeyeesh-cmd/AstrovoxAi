"""
Advanced training infrastructure for large-scale model training.
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F
import math

logger = logging.getLogger(__name__)


class GradientCheckpointingWrapper(nn.Module):
    def __init__(self, module: nn.Module, use_reentrant: bool = False):
        super().__init__()
        self.module = module
        self.use_reentrant = use_reentrant

    def forward(self, *args, **kwargs):
        return torch.utils.checkpoint.checkpoint(self.module, *args, use_reentrant=self.use_reentrant, **kwargs)


class ZeROOptimizer:
    def __init__(self, model: nn.Module, optimizer: torch.optim.Optimizer, stage: int = 2):
        self.model = model
        self.optimizer = optimizer
        self.stage = stage
        self.param_groups: Dict[str, List[nn.Parameter]] = {}
        for name, param in model.named_parameters():
            if param.requires_grad:
                self.param_groups[name] = [param]

    def step(self, loss: torch.Tensor) -> None:
        self.optimizer.zero_grad()
        loss.backward()
        if self.stage >= 1:
            self._allreduce_gradients()
        self.optimizer.step()

    def _allreduce_gradients(self) -> None:
        for param in self.model.parameters():
            if param.grad is not None:
                torch.distributed.all_reduce(param.grad, op=torch.distributed.ReduceOp.SUM)


class PipelineSchedule:
    def __init__(self, num_microbatches: int, num_stages: int):
        self.num_microbatches = num_microbatches
        self.num_stages = num_stages

    def get_forward_schedule(self) -> List[Tuple[int, int]]:
        schedule = []
        for t in range(self.num_microbatches):
            for s in range(self.num_stages):
                schedule.append((t, s))
        return schedule

    def get_backward_schedule(self) -> List[Tuple[int, int]]:
        schedule = []
        for t in reversed(range(self.num_microbatches)):
            for s in reversed(range(self.num_stages)):
                schedule.append((t, s))
        return schedule


class AdvancedTrainLoop:
    def __init__(self, model: nn.Module, config: Any, train_loader: Any, val_loader: Optional[Any] = None):
        self.model = model
        self.config = config
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.optimizer = torch.optim.AdamW(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)
        self.global_step = 0
        self.best_val_loss = float('inf')

    def train_epoch(self, epoch: int) -> Dict[str, float]:
        self.model.train()
        total_loss = 0.0
        num_batches = 0
        for batch in self.train_loader:
            loss = self.train_step(batch)
            total_loss += loss
            num_batches += 1
            self.global_step += 1
        return {'train_loss': total_loss / max(num_batches, 1)}

    def train_step(self, batch: Dict[str, torch.Tensor]) -> float:
        self.optimizer.zero_grad()
        input_ids = batch.get("input_ids")
        labels = batch.get("labels", input_ids)
        logits = self.model(input_ids)
        shift_logits = logits[..., :-1, :].contiguous()
        shift_labels = labels[..., 1:].contiguous()
        loss = F.cross_entropy(shift_logits.view(-1, shift_logits.size(-1)), shift_labels.view(-1))
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.config.clip_grad_norm)
        self.optimizer.step()
        return loss.item()

    def validate(self) -> Dict[str, float]:
        if self.val_loader is None:
            return {}
        self.model.eval()
        total_loss = 0.0
        num_batches = 0
        with torch.no_grad():
            for batch in self.val_loader:
                input_ids = batch.get("input_ids")
                labels = batch.get("labels", input_ids)
                logits = self.model(input_ids)
                shift_logits = logits[..., :-1, :].contiguous()
                shift_labels = labels[..., 1:].contiguous()
                loss = F.cross_entropy(shift_logits.view(-1, shift_logits.size(-1)), shift_labels.view(-1))
                total_loss += loss.item()
                num_batches += 1
        val_loss = total_loss / max(num_batches, 1)
        if val_loss < self.best_val_loss:
            self.best_val_loss = val_loss
        return {'val_loss': val_loss, 'best_val_loss': self.best_val_loss}
