from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


@dataclass
class SparsityConfig:
    sparsity_ratio: float = 0.5
    method: str = "magnitude"
    block_size: int = 4
    prune_biases: bool = False


class SparseLinear(nn.Module):
    def __init__(
        self,
        in_features: int,
        out_features: int,
        bias: bool = True,
        sparsity: float = 0.5,
        block_size: int = 4,
    ) -> None:
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.sparsity = sparsity
        self.block_size = block_size

        self.weight = nn.Parameter(torch.empty(out_features, in_features))
        if bias:
            self.bias = nn.Parameter(torch.zeros(out_features))
        else:
            self.register_parameter("bias", None)
        self.mask = nn.Parameter(torch.ones_like(self.weight), requires_grad=False)
        self._reset_parameters()

    def _reset_parameters(self) -> None:
        nn.init.kaiming_uniform_(self.weight, a=5**0.5)
        if self.bias is not None:
            nn.init.zeros_(self.bias)

    def apply_sparsity(self) -> None:
        with torch.no_grad():
            w = self.weight.data
            abs_w = w.abs()

            if self.block_size > 1:
                flat = abs_w.flatten(1)
                num_blocks = flat.shape[1] // self.block_size
                if flat.shape[1] % self.block_size != 0:
                    padding = self.block_size - (flat.shape[1] % self.block_size)
                    flat = F.pad(flat, (0, padding))
                block_sums = flat[:, :num_blocks * self.block_size].reshape(
                    flat.shape[0], num_blocks, self.block_size
                ).sum(dim=-1)
                k = max(1, int(num_blocks * self.sparsity))
                _, indices = torch.topk(block_sums, k, largest=False)
                mask = torch.ones_like(block_sums)
                mask.scatter_(1, indices, 0)
                mask = mask.repeat_interleave(self.block_size, dim=1)
                mask = mask[:, :w.shape[1]]
                self.mask.data = mask.reshape(w.shape).to(w.device)
            else:
                k = max(1, int(w.numel() * self.sparsity))
                _, indices = torch.topk(abs_w.flatten(), k, largest=False)
                mask = torch.ones_like(w.flatten())
                mask.scatter_(0, indices, 0)
                self.mask.data = mask.reshape(w.shape).to(w.device)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return F.linear(x, self.weight * self.mask, self.bias)


class MaskedTrainer:
    def __init__(self, model: nn.Module, config: SparsityConfig) -> None:
        self.model = model
        self.config = config
        self.step_count = 0

    def step(self) -> None:
        self.step_count += 1

    def apply_mask(self) -> None:
        for module in self.model.modules():
            if isinstance(module, SparseLinear):
                module.apply_sparsity()

    def train_step(
        self,
        inputs: torch.Tensor,
        labels: torch.Tensor,
        optimizer: torch.optim.Optimizer,
    ) -> torch.Tensor:
        self.model.train()
        optimizer.zero_grad()
        outputs = self.model(inputs)
        if outputs.shape == labels.shape:
            loss = F.mse_loss(outputs, labels)
        else:
            loss = outputs.loss if hasattr(outputs, "loss") else F.cross_entropy(outputs, labels)
        loss.backward()
        optimizer.step()
        self.step()
        self.apply_mask()
        return loss


def set_sparsity_ratio(model: nn.Module, ratio: float) -> None:
    for module in model.modules():
        if isinstance(module, SparseLinear):
            module.sparsity = ratio
            module.apply_sparsity()
