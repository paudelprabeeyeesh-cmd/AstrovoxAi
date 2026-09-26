"""
Fine-tuning pipeline for local model adaptation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset

from app.fine_tune.lora import LoRA
from app.fine_tune.qlora import QLoRA

logger = logging.getLogger(__name__)


@dataclass
class FineTuneConfig:
    lr: float = 1e-4
    weight_decay: float = 0.01
    batch_size: int = 8
    num_epochs: int = 3
    max_grad_norm: float = 1.0
    lora_rank: int = 8
    lora_alpha: float = 16.0
    lora_dropout: float = 0.0
    use_qlora: bool = False
    qlora_bits: int = 4


class FineTuningPipeline:
    def __init__(self, model: nn.Module, train_dataset: Dataset, val_dataset: Optional[Dataset] = None, config: Optional[FineTuneConfig] = None):
        self.model = model
        self.train_dataset = train_dataset
        self.val_dataset = val_dataset
        self.config = config or FineTuneConfig()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)

        if self.config.use_qlora:
            qlora = QLoRA(bits=self.config.qlora_bits, lora_rank=self.config.lora_rank, lora_alpha=self.config.lora_alpha)
            self.model = qlora.prepare(self.model)
        else:
            LoRA.inject(self.model, rank=self.config.lora_rank, alpha=self.config.lora_alpha, dropout=self.config.lora_dropout)

        self.train_loader = DataLoader(train_dataset, batch_size=self.config.batch_size, shuffle=True, pin_memory=True)
        self.val_loader = DataLoader(val_dataset, batch_size=self.config.batch_size, shuffle=False, pin_memory=True) if val_dataset else None
        self.optimizer = torch.optim.AdamW(self.model.parameters(), lr=self.config.lr, weight_decay=self.config.weight_decay)
        self.scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(self.optimizer, T_max=self.config.num_epochs)

    def train(self, loss_fn: Optional[Callable] = None) -> Dict[str, float]:
        loss_fn = loss_fn or F.cross_entropy
        self.model.train()
        total_loss = 0.0
        for epoch in range(self.config.num_epochs):
            epoch_loss = 0.0
            for batch in self.train_loader:
                input_ids = batch["input_ids"].to(self.device)
                labels = batch.get("labels", input_ids).to(self.device)
                logits = self.model(input_ids)
                loss = loss_fn(logits.view(-1, logits.size(-1)), labels.view(-1))
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.config.max_grad_norm)
                self.optimizer.step()
                self.optimizer.zero_grad()
                epoch_loss += loss.item()
            self.scheduler.step()
            total_loss = epoch_loss / max(len(self.train_loader), 1)
            if self.val_loader:
                val_loss = self.validate(loss_fn)
                logger.info("Epoch %d: train_loss=%.4f val_loss=%.4f", epoch + 1, total_loss, val_loss)
        return {"final_train_loss": total_loss}

    def validate(self, loss_fn: Callable = F.cross_entropy) -> float:
        self.model.eval()
        total_loss = 0.0
        with torch.no_grad():
            for batch in self.val_loader:
                input_ids = batch["input_ids"].to(self.device)
                labels = batch.get("labels", input_ids).to(self.device)
                logits = self.model(input_ids)
                loss = loss_fn(logits.view(-1, logits.size(-1)), labels.view(-1))
                total_loss += loss.item()
        return total_loss / max(len(self.val_loader), 1)

    def save(self, path: str) -> None:
        torch.save({"model": self.model.state_dict(), "config": self.config.__dict__}, path)
