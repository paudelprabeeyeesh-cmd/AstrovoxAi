"""
Knowledge distillation pipeline: teacher-student training.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


@dataclass
class DistillationConfig:
    temperature: float = 2.0
    alpha: float = 0.5
    epochs: int = 3
    batch_size: int = 8


class DistillationLoss(nn.Module):
    """Combined hard and soft loss for knowledge distillation."""

    def __init__(self, temperature: float = 2.0, alpha: float = 0.5):
        super().__init__()
        self.temperature = temperature
        self.alpha = alpha

    def forward(self, student_logits: torch.Tensor, teacher_logits: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        soft_loss = F.kl_div(
            F.log_softmax(student_logits / self.temperature, dim=-1),
            F.softmax(teacher_logits / self.temperature, dim=-1),
            reduction="batchmean",
        ) * (self.temperature ** 2)
        hard_loss = F.cross_entropy(student_logits, labels)
        return self.alpha * soft_loss + (1 - self.alpha) * hard_loss


class KnowledgeDistillationPipeline:
    """Teacher-student distillation pipeline."""

    def __init__(self, teacher_model: nn.Module, student_model: nn.Module, config: Optional[DistillationConfig] = None):
        self.teacher = teacher_model
        self.student = student_model
        self.config = config or DistillationConfig()
        self.teacher.eval()
        self.student.train()
        self.loss_fn = DistillationLoss(temperature=self.config.temperature, alpha=self.config.alpha)
        self.optimizer = torch.optim.AdamW(self.student.parameters(), lr=1e-4)

    def train_step(self, batch: dict) -> float:
        input_ids = batch["input_ids"]
        labels = batch["labels"]
        with torch.no_grad():
            teacher_logits = self.teacher(input_ids)
        student_logits = self.student(input_ids)
        loss = self.loss_fn(student_logits, teacher_logits, labels)
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.student.parameters(), 1.0)
        self.optimizer.step()
        return loss.item()

    def distill_dataset(self, dataloader) -> float:
        total_loss = 0.0
        steps = 0
        for batch in dataloader:
            loss = self.train_step(batch)
            total_loss += loss
            steps += 1
        return total_loss / max(steps, 1)
