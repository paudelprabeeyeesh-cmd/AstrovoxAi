"""
Training engine with mixed precision, AdamW, cosine scheduler, and gradient clipping.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


@dataclass
class TrainConfig:
    learning_rate: float = 1e-4
    weight_decay: float = 0.01
    warmup_steps: int = 100
    max_steps: int = 1000
    clip_grad_norm: float = 1.0
    use_amp: bool = False


class CosineLRScheduler:
    """Cosine learning rate scheduler with linear warmup."""

    def __init__(self, optimizer: torch.optim.Optimizer, config: TrainConfig):
        self.optimizer = optimizer
        self.config = config
        self.step_count = 0
        self.base_lrs = [group["lr"] for group in optimizer.param_groups]

    def step(self):
        self.step_count += 1
        if self.step_count <= self.config.warmup_steps:
            scale = self.step_count / self.config.warmup_steps
        else:
            progress = (self.step_count - self.config.warmup_steps) / max(1, self.config.max_steps - self.config.warmup_steps)
            scale = 0.5 * (1.0 + math.cos(math.pi * min(progress, 1.0)))
        for group, base_lr in zip(self.optimizer.param_groups, self.base_lrs):
            group["lr"] = base_lr * scale


class AdamW(torch.optim.Optimizer):
    """AdamW optimizer from scratch."""

    def __init__(self, params, lr=1e-4, betas=(0.9, 0.999), eps=1e-8, weight_decay=0.01):
        defaults = dict(lr=lr, betas=betas, eps=eps, weight_decay=weight_decay)
        super().__init__(params, defaults)

    @torch.no_grad()
    def step(self, closure=None):
        loss = None
        if closure is not None:
            with torch.enable_grad():
                loss = closure()
        for group in self.param_groups:
            beta1, beta2 = group["betas"]
            for p in group["params"]:
                if p.grad is None:
                    continue
                grad = p.grad
                state = self.state[p]
                if len(state) == 0:
                    state["exp_avg"] = torch.zeros_like(p)
                    state["exp_avg_sq"] = torch.zeros_like(p)
                exp_avg, exp_avg_sq = state["exp_avg"], state["exp_avg_sq"]
                exp_avg.mul_(beta1).add_(grad, alpha=1 - beta1)
                exp_avg_sq.mul_(beta2).addcmul_(grad, grad, value=1 - beta2)
                denom = exp_avg_sq.sqrt().add_(group["eps"])
                step_size = group["lr"]
                if group["weight_decay"] != 0:
                    p.mul_(1 - group["lr"] * group["weight_decay"])
                p.addcdiv_(exp_avg, denom, value=-step_size)
        return loss


class MixedPrecisionTrainer:
    """Mixed precision trainer with BF16 forward/backward and FP32 master weights."""

    def __init__(self, model: nn.Module, config: TrainConfig):
        self.model = model
        self.config = config
        self.optimizer = AdamW(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)
        self.scheduler = CosineLRScheduler(self.optimizer, config)
        self.scaler = torch.cuda.amp.GradScaler(enabled=config.use_amp)
        self.global_step = 0

    def train_step(self, batch: dict) -> float:
        input_ids = batch["input_ids"]
        attention_mask = batch.get("attention_mask")
        labels = batch["labels"]
        with torch.cuda.amp.autocast(enabled=self.config.use_amp):
            logits = self.model(input_ids, attention_mask=attention_mask)
            shift_logits = logits[..., :-1, :].contiguous()
            shift_labels = labels[..., 1:].contiguous()
            loss = F.cross_entropy(shift_logits.view(-1, shift_logits.size(-1)), shift_labels.view(-1))
        self.scaler.scale(loss).backward()
        self.scaler.unscale_(self.optimizer)
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.config.clip_grad_norm)
        self.scaler.step(self.optimizer)
        self.scaler.update()
        self.scheduler.step()
        self.global_step += 1
        return loss.item()

    def save_checkpoint(self, path: str):
        torch.save({
            "model_state_dict": self.model.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "global_step": self.global_step,
        }, path)

    def load_checkpoint(self, path: str):
        ckpt = torch.load(path, map_location="cpu")
        self.model.load_state_dict(ckpt["model_state_dict"])
        self.optimizer.load_state_dict(ckpt["optimizer_state_dict"])
        self.global_step = ckpt["global_step"]
