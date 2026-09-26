from typing import Optional, Dict, Any, List
import torch
import torch.nn as nn
import logging

logger = logging.getLogger(__name__)


class KnowledgeDistiller:
    def __init__(self, teacher: nn.Module, student: nn.Module, temperature: float = 2.0, alpha: float = 0.5):
        self.teacher = teacher.eval()
        self.student = student
        self.temperature = temperature
        self.alpha = alpha
        self.ce_loss = nn.CrossEntropyLoss()
        self.kl_loss = nn.KLDivLoss(reduction='batchmean')

    def distill_step(self, inputs: torch.Tensor, labels: torch.Tensor, optimizer: torch.optim.Optimizer) -> float:
        with torch.no_grad():
            teacher_logits = self.teacher(inputs) / self.temperature
        student_logits = self.student(inputs) / self.temperature
        soft_loss = self.kl_loss(torch.log_softmax(student_logits, dim=-1), torch.softmax(teacher_logits, dim=-1)) * (self.temperature ** 2)
        hard_loss = self.ce_loss(student_logits, labels)
        loss = self.alpha * soft_loss + (1 - self.alpha) * hard_loss
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        return loss.item()

    def distill_epoch(self, dataloader, optimizer: torch.optim.Optimizer) -> float:
        total_loss = 0.0
        num_batches = 0
        for batch in dataloader:
            inputs = batch['input_ids'] if isinstance(batch, dict) else batch[0]
            labels = batch['labels'] if isinstance(batch, dict) else batch[1]
            loss = self.distill_step(inputs, labels, optimizer)
            total_loss += loss
            num_batches += 1
        return total_loss / max(1, num_batches)
