from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


@dataclass
class DistillationConfig:
    temperature: float = 2.0
    alpha: float = 0.5
    feature_layers: list[str] | None = None
    use_feature_distillation: bool = False


class DistillationTrainer:
    def __init__(
        self,
        teacher: nn.Module,
        student: nn.Module,
        config: DistillationConfig,
    ) -> None:
        self.teacher = teacher
        self.student = student
        self.config = config
        self.teacher.eval()
        self.teacher_features: dict[str, torch.Tensor] = {}
        self.student_features: dict[str, torch.Tensor] = {}

        if config.use_feature_distillation and config.feature_layers:
            self._register_hooks()

    def _register_hooks(self) -> None:
        def get_activation(name: str, storage: dict[str, torch.Tensor]) -> Callable:
            def hook(module: nn.Module, input: Any, output: Any) -> None:
                storage[name] = output.detach() if isinstance(output, torch.Tensor) else output[0].detach()
            return hook

        for name, module in self.teacher.named_modules():
            if name in (self.config.feature_layers or []):
                module.register_forward_hook(get_activation(name, self.teacher_features))
        for name, module in self.student.named_modules():
            if name in (self.config.feature_layers or []):
                module.register_forward_hook(get_activation(name, self.student_features))

    def compute_loss(self, inputs: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            teacher_outputs = self.teacher(inputs)

        student_outputs = self.student(inputs)

        teacher_logits = teacher_outputs.logits if hasattr(teacher_outputs, "logits") else teacher_outputs
        student_logits = student_outputs.logits if hasattr(student_outputs, "logits") else student_outputs

        soft_teacher = F.softmax(teacher_logits / self.config.temperature, dim=-1)
        soft_student = F.log_softmax(student_logits / self.config.temperature, dim=-1)
        distillation_loss = F.kl_div(soft_student, soft_teacher, reduction="batchmean") * (self.config.temperature ** 2)

        ce_loss = F.cross_entropy(student_logits, labels)
        total_loss = self.config.alpha * distillation_loss + (1 - self.config.alpha) * ce_loss

        if self.config.use_feature_distillation and self.config.feature_layers:
            feature_loss = 0.0
            count = 0
            for name in self.config.feature_layers or []:
                if name in self.teacher_features and name in self.student_features:
                    feature_loss += F.mse_loss(self.student_features[name], self.teacher_features[name])
                    count += 1
            if count > 0:
                total_loss += 0.1 * feature_loss / count

        return total_loss

    def train_step(
        self,
        inputs: torch.Tensor,
        labels: torch.Tensor,
        optimizer: torch.optim.Optimizer,
    ) -> torch.Tensor:
        self.student.train()
        optimizer.zero_grad()
        loss = self.compute_loss(inputs, labels)
        loss.backward()
        optimizer.step()
        return loss


class TemperatureSoftTargetLoss(nn.Module):
    def __init__(self, temperature: float = 2.0, alpha: float = 0.5):
        super().__init__()
        self.temperature = temperature
        self.alpha = alpha

    def forward(
        self,
        student_logits: torch.Tensor,
        teacher_logits: torch.Tensor,
        labels: torch.Tensor,
    ) -> torch.Tensor:
        soft_teacher = F.softmax(teacher_logits / self.temperature, dim=-1)
        soft_student = F.log_softmax(student_logits / self.temperature, dim=-1)
        distillation_loss = F.kl_div(soft_student, soft_teacher, reduction="batchmean") * (self.temperature ** 2)
        ce_loss = F.cross_entropy(student_logits, labels)
        return self.alpha * distillation_loss + (1 - self.alpha) * ce_loss


class FeatureDistillationLoss(nn.Module):
    def __init__(
        self,
        feature_layers: list[str] | None = None,
        weight: float = 0.1,
    ):
        super().__init__()
        self.feature_layers = feature_layers or []
        self.weight = weight
        self.teacher_features: dict[str, torch.Tensor] = {}
        self.student_features: dict[str, torch.Tensor] = {}

    def register_hooks(self, teacher: nn.Module, student: nn.Module) -> None:
        def get_activation(name: str, storage: dict[str, torch.Tensor]) -> Callable:
            def hook(module: nn.Module, input: Any, output: Any) -> None:
                storage[name] = output.detach() if isinstance(output, torch.Tensor) else output[0].detach()
            return hook

        for name, module in teacher.named_modules():
            if name in self.feature_layers:
                module.register_forward_hook(get_activation(name, self.teacher_features))
        for name, module in student.named_modules():
            if name in self.feature_layers:
                module.register_forward_hook(get_activation(name, self.student_features))

    def forward(self) -> torch.Tensor:
        loss = torch.tensor(0.0)
        for name in self.feature_layers:
            if name in self.teacher_features and name in self.student_features:
                loss = loss + F.mse_loss(self.student_features[name], self.teacher_features[name])
        return self.weight * loss / max(len(self.feature_layers), 1)
