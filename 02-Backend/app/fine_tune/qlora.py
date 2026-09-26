"""
QLoRA (Quantized LoRA) implementation.
"""

from __future__ import annotations

from typing import List, Optional

import torch
import torch.nn as nn

from app.fine_tune.lora import LoRA


class QLoRA:
    def __init__(self, bits: int = 4, group_size: int = 128, lora_rank: int = 8, lora_alpha: float = 16.0):
        self.bits = bits
        self.group_size = group_size
        self.lora_rank = lora_rank
        self.lora_alpha = lora_alpha

    def prepare(self, model: nn.Module, target_modules: Optional[List[str]] = None) -> nn.Module:
        model = self._quantize_model(model)
        model = LoRA.inject(model, target_modules, rank=self.lora_rank, alpha=self.lora_alpha)
        for name, param in model.named_parameters():
            if "lora" in name:
                param.requires_grad = True
            else:
                param.requires_grad = False
        return model

    def _quantize_model(self, model: nn.Module) -> nn.Module:
        for name, module in model.named_modules():
            if isinstance(module, nn.Linear):
                weight = module.weight.data.float()
                scale = weight.abs().mean(dim=1, keepdim=True).clamp(min=1e-6)
                q = torch.clamp(torch.round(weight / scale), -8, 7).to(torch.int8)
                module.weight.data = q.float()
                module.register_buffer("quant_scale", scale)
        return model
