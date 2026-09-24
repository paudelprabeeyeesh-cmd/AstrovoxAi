"""
QAT (Quantization-Aware Training): fake quantization with straight-through estimator.
"""

from __future__ import annotations

from typing import List

import torch
import torch.nn as nn
import torch.nn.functional as F


class FakeQuantize(nn.Module):
    """Fake quantization module for QAT with straight-through estimator."""

    def __init__(self, n_bits: int = 8, symmetric: bool = True):
        super().__init__()
        self.n_bits = n_bits
        self.symmetric = symmetric
        self.register_buffer("min_val", torch.tensor(0.0))
        self.register_buffer("max_val", torch.tensor(0.0))
        self.observer_enabled = True

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.training:
            if self.observer_enabled:
                self.min_val = torch.min(self.min_val, x.min())
                self.max_val = torch.max(self.max_val, x.max())
            scale = (self.max_val - self.min_val) / (2 ** self.n_bits - 1)
            zero_point = 0 if self.symmetric else torch.round(-self.min_val / scale)
            x_quant = torch.clamp(torch.round(x / scale + zero_point), 0, 2 ** self.n_bits - 1)
            x_dequant = (x_quant - zero_point) * scale
            return x + (x_dequant - x).detach()
        return x


class QATTrainer:
    """Quantization-Aware Training loop."""

    def __init__(self, model: nn.Module, config: dict):
        self.model = model
        self.config = config
        self.fake_quant_modules = self._insert_fake_quant()
        self.optimizer = torch.optim.AdamW(model.parameters(), lr=1e-5)

    def _insert_fake_quant(self) -> List[FakeQuantize]:
        modules = []
        for name, module in self.model.named_modules():
            if isinstance(module, nn.Linear):
                fq = FakeQuantize(n_bits=8)
                modules.append(fq)
        return modules

    def train_step(self, batch: dict) -> float:
        input_ids = batch["input_ids"]
        labels = batch["labels"]
        logits = self.model(input_ids)
        shift_logits = logits[..., :-1, :].contiguous()
        shift_labels = labels[..., 1:].contiguous()
        loss = F.cross_entropy(shift_logits.view(-1, shift_logits.size(-1)), shift_labels.view(-1))
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
        self.optimizer.step()
        return loss.item()
