from typing import Optional, Dict, Callable
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset


class FineTuningPipeline:
    def __init__(self, model: nn.Module, train_dataset: Dataset, val_dataset: Optional[Dataset] = None, optimizer_cls=torch.optim.AdamW, lr: float = 1e-4, weight_decay: float = 0.01, batch_size: int = 8, num_epochs: int = 3, gradient_accumulation_steps: int = 1, max_grad_norm: float = 1.0, device: str = 'cuda'):
        self.model = model
        self.train_dataset = train_dataset
        self.val_dataset = val_dataset
        self.lr = lr
        self.weight_decay = weight_decay
        self.batch_size = batch_size
        self.num_epochs = num_epochs
        self.gradient_accumulation_steps = gradient_accumulation_steps
        self.max_grad_norm = max_grad_norm
        self.device = device
        self.train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, pin_memory=True, num_workers=4)
        self.val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, pin_memory=True, num_workers=4) if val_dataset else None
        self.optimizer = optimizer_cls(model.parameters(), lr=lr, weight_decay=weight_decay)
        self.scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(self.optimizer, T_max=num_epochs)

    def train(self, loss_fn: Callable = F.cross_entropy) -> Dict[str, float]:
        self.model.train()
        self.model.to(self.device)
        total_loss = 0.0
        for epoch in range(self.num_epochs):
            epoch_loss = 0.0
            self.optimizer.zero_grad()
            for step, batch in enumerate(self.train_loader):
                input_ids = batch['input_ids'].to(self.device)
                labels = batch.get('labels', input_ids).to(self.device)
                logits = self.model(input_ids)
                loss = loss_fn(logits.view(-1, logits.size(-1)), labels.view(-1))
                loss = loss / self.gradient_accumulation_steps
                loss.backward()
                if (step + 1) % self.gradient_accumulation_steps == 0:
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.max_grad_norm)
                    self.optimizer.step()
                    self.optimizer.zero_grad()
                epoch_loss += loss.item() * self.gradient_accumulation_steps
            self.scheduler.step()
            total_loss = epoch_loss / len(self.train_loader)
            if self.val_loader:
                val_loss = self.validate(loss_fn)
        return {'final_train_loss': total_loss}

    def validate(self, loss_fn: Callable = F.cross_entropy) -> float:
        self.model.eval()
        total_loss = 0.0
        with torch.no_grad():
            for batch in self.val_loader:
                input_ids = batch['input_ids'].to(self.device)
                labels = batch.get('labels', input_ids).to(self.device)
                logits = self.model(input_ids)
                loss = loss_fn(logits.view(-1, logits.size(-1)), labels.view(-1))
                total_loss += loss.item()
        return total_loss / len(self.val_loader)

    def save(self, path: str) -> None:
        torch.save({'model': self.model.state_dict(), 'optimizer': self.optimizer.state_dict()}, path)

    def load(self, path: str) -> None:
        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model'])
        self.optimizer.load_state_dict(checkpoint['optimizer'])
