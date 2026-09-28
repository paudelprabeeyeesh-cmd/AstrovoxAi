from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


@dataclass
class PruningConfig:
    sparsity: float = 0.5
    schedule: str = "linear"
    start_step: int = 0
    end_step: int = 1000
    block_size: int = 1
    prune_biases: bool = False


class MagnitudePruner:
    def __init__(self, model: nn.Module, config: PruningConfig) -> None:
        self.model = model
        self.config = config
        self.masks: dict[str, torch.Tensor] = {}
        self.current_sparsity: float = 0.0

    def _get_target_modules(self) -> list[tuple[str, nn.Module]]:
        modules = []
        for name, module in self.model.named_modules():
            if isinstance(module, (nn.Linear, nn.Conv2d)):
                modules.append((name, module))
        return modules

    def compute_masks(self, sparsity: float) -> None:
        for name, module in self._get_target_modules():
            weight = module.weight.data
            abs_weight = weight.abs()

            if self.config.block_size > 1 and isinstance(module, nn.Linear):
                flat = abs_weight.flatten(1)
                num_blocks = flat.shape[1] // self.config.block_size
                if flat.shape[1] % self.config.block_size != 0:
                    padding = self.config.block_size - (flat.shape[1] % self.config.block_size)
                    flat = F.pad(flat, (0, padding))
                block_sums = flat[:, :num_blocks * self.config.block_size].reshape(
                    flat.shape[0], num_blocks, self.config.block_size
                ).sum(dim=-1)
                k = max(1, int(num_blocks * sparsity))
                threshold = torch.topk(block_sums, k, largest=False).values[:, -1]
                mask = block_sums >= threshold.unsqueeze(1)
                mask = mask.repeat_interleave(self.config.block_size, dim=1)
                mask = mask[:, :weight.shape[1]]
                self.masks[name] = mask.reshape(weight.shape).to(weight.device)
            else:
                k = max(1, int(weight.numel() * sparsity))
                threshold = torch.topk(abs_weight.flatten(), k, largest=False).values[-1]
                self.masks[name] = (abs_weight >= threshold).reshape(weight.shape).to(weight.device)

    def apply_masks(self) -> None:
        for name, module in self._get_target_modules():
            if name in self.masks:
                module.weight.data *= self.masks[name]

    def step(self, current_step: int) -> None:
        if current_step < self.config.start_step:
            return
        if current_step >= self.config.end_step:
            target_sparsity = self.config.sparsity
        else:
            progress = (current_step - self.config.start_step) / max(1, self.config.end_step - self.config.start_step)
            target_sparsity = self.config.sparsity * progress

        self.current_sparsity = target_sparsity
        self.compute_masks(target_sparsity)
        self.apply_masks()

    def get_sparsity(self) -> float:
        total = 0
        zeros = 0
        for _, module in self._get_target_modules():
            w = module.weight.data
            total += w.numel()
            zeros += (w == 0).sum().item()
        return zeros / max(total, 1)


class StructuredSparsity:
    def __init__(self, model: nn.Module, sparsity: float = 0.5) -> None:
        self.model = model
        self.sparsity = sparsity

    def apply(self) -> None:
        for name, module in self.model.named_modules():
            if isinstance(module, nn.Linear):
                weight = module.weight.data
                out_features, in_features = weight.shape
                num_keep = max(1, int(in_features * (1 - self.sparsity)))
                norms = weight.abs().sum(dim=0)
                _, indices = torch.topk(norms, num_keep)
                mask = torch.zeros_like(weight)
                mask[:, indices] = 1.0
                module.weight.data *= mask
