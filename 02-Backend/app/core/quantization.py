"""
Quantization implementations: AWQ, GPTQ, and QAT.
"""

from __future__ import annotations

import logging
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


def quantize_weight_int4(weight: torch.Tensor, scale: torch.Tensor) -> torch.Tensor:
    """Quantize weights to INT4."""
    max_val = 7.0
    min_val = -8.0
    scale = scale.to(weight.device)
    while scale.dim() < weight.dim():
        scale = scale.unsqueeze(-1)
    scaled = weight / scale
    quantized = torch.clamp(torch.round(scaled), min_val, max_val).to(torch.int8)
    return quantized


def dequantize_weight_int4(quantized: torch.Tensor, scale: torch.Tensor) -> torch.Tensor:
    """Dequantize INT4 weights back to FP16/FP32."""
    scale = scale.to(quantized.device)
    while scale.dim() < quantized.dim():
        scale = scale.unsqueeze(-1)
    return quantized.float() * scale


def awq_quantize(weight: torch.Tensor, activation: torch.Tensor, n_bits: int = 4) -> Tuple[torch.Tensor, torch.Tensor]:
    """Activation-aware Weight Quantization (AWQ).
    
    Computes per-channel scale factors based on activation magnitudes.
    """
    act_magnitudes = activation.abs().mean(dim=0)
    salient_weights = weight.abs().mean(dim=1)
    importance = act_magnitudes.unsqueeze(0) * salient_weights.unsqueeze(1)
    scale = importance.clamp(min=1e-6)
    quantized = quantize_weight_int4(weight, scale)
    return quantized, scale


def gptq_quantize(weight: torch.Tensor, hessian: torch.Tensor, n_bits: int = 4, blocksize: int = 128) -> Tuple[torch.Tensor, torch.Tensor]:
    """GPTQ-style layer-wise quantization with Hessian-based error compensation."""
    out_features, in_features = weight.shape
    quantized = torch.zeros_like(weight, dtype=torch.int8)
    scales = torch.zeros(in_features, device=weight.device)
    for i in range(0, in_features, blocksize):
        block_end = min(i + blocksize, in_features)
        block_weight = weight[:, i:block_end]
        block_size = block_end - i
        block_hessian = hessian[i:block_end, i:block_end]
        try:
            L = torch.linalg.cholesky(block_hessian + 1e-4 * torch.eye(block_size, device=weight.device))
            scale = torch.diag(L)
            if scale.numel() == 0:
                scale = block_weight.abs().max(dim=1)[0].clamp(min=1e-6)
        except RuntimeError:
            scale = block_weight.abs().max(dim=1)[0].clamp(min=1e-6)
        q_block = quantize_weight_int4(block_weight, scale)
        quantized[:, i:block_end] = q_block
        scales[i:block_end] = scale
    return quantized, scales


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
        if self.observer_enabled:
            self.min_val = torch.min(self.min_val, x.min())
            self.max_val = torch.max(self.max_val, x.max())
        if self.training:
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
