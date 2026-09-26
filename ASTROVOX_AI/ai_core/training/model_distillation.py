from typing import Optional, Dict
import torch
import torch.nn as nn
import torch.nn.functional as F


class ModelDistiller:
    def __init__(self, teacher: nn.Module, student: nn.Module, temperature: float = 2.0, alpha: float = 0.5):
        self.teacher = teacher
        self.student = student
        self.temperature = temperature
        self.alpha = alpha
        self.kl_loss = nn.KLDivLoss(reduction='batchmean')

    def distillation_step(self, input_ids: torch.Tensor, labels: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, Dict[str, float]]:
        self.teacher.eval()
        self.student.train()
        with torch.no_grad():
            teacher_logits = self.teacher(input_ids)
        student_logits = self.student(input_ids)
        soft_loss = self.kl_loss(F.log_softmax(student_logits / self.temperature, dim=-1), F.softmax(teacher_logits / self.temperature, dim=-1)) * (self.temperature ** 2)
        if labels is not None:
            hard_loss = F.cross_entropy(student_logits.view(-1, student_logits.size(-1)), labels.view(-1))
            total_loss = self.alpha * soft_loss + (1 - self.alpha) * hard_loss
        else:
            total_loss = soft_loss
        return total_loss, {'soft_loss': soft_loss.item()}

    def train(self, train_loader, num_epochs: int = 3, device: str = 'cuda') -> None:
        optimizer = torch.optim.AdamW(self.student.parameters(), lr=1e-4)
        self.teacher.to(device)
        self.student.to(device)
        for epoch in range(num_epochs):
            total_loss = 0.0
            for batch in train_loader:
                input_ids = batch['input_ids'].to(device)
                labels = batch.get('labels')
                if labels is not None:
                    labels = labels.to(device)
                loss, _ = self.distillation_step(input_ids, labels)
                loss.backward()
                optimizer.step()
                optimizer.zero_grad()
                total_loss += loss.item()
