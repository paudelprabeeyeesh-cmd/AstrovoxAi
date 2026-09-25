"""
Model distillation with knowledge transfer and temperature scaling.
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


class KnowledgeDistiller:
    def __init__(self, teacher_model: nn.Module, student_model: nn.Module, temperature: float = 2.0, alpha: float = 0.5):
        self.teacher_model = teacher_model
        self.student_model = student_model
        self.temperature = temperature
        self.alpha = alpha

    def distillation_loss(self, student_logits: torch.Tensor, teacher_logits: torch.Tensor, labels: torch.Tensor) -> Tuple[torch.Tensor, Dict[str, float]]:
        soft_targets = F.softmax(teacher_logits / self.temperature, dim=-1)
        soft_prob = F.log_softmax(student_logits / self.temperature, dim=-1)
        soft_loss = -(soft_targets * soft_prob).sum(dim=-1).mean() * (self.temperature ** 2)
        hard_loss = F.cross_entropy(student_logits, labels)
        total_loss = self.alpha * soft_loss + (1 - self.alpha) * hard_loss
        return total_loss, {'soft_loss': soft_loss.item(), 'hard_loss': hard_loss.item(), 'total_loss': total_loss.item()}

    def train_step(self, input_ids: torch.Tensor, labels: torch.Tensor, optimizer: torch.optim.Optimizer) -> Dict[str, float]:
        self.teacher_model.eval()
        self.student_model.train()
        with torch.no_grad():
            teacher_logits = self.teacher_model(input_ids)
        student_logits = self.student_model(input_ids)
        loss, metrics = self.distillation_loss(student_logits, teacher_logits, labels)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        return metrics
