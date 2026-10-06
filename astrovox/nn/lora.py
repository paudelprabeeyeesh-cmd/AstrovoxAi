"""LoRA/QLoRA integration for efficient fine-tuning.

Implements Low-Rank Adaptation (LoRA) and its quantized variant (QLoRA) as
drop-in replacements for linear layers during fine-tuning.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from astrovox.nn.linear import Linear
from astrovox.tensor.tensor import Tensor


@dataclass
class LoRAConfig:
    rank: int = 4
    alpha: int = 16
    dropout: float = 0.0
    quantize: bool = False


class LoRALinear(Linear):
    """Linear layer with LoRA adapters."""

    def __init__(self, in_features: int, out_features: int, config: LoRAConfig | None = None, bias: bool = True) -> None:
        super().__init__(in_features, out_features, bias=bias)
        self.lora_config = config or LoRAConfig()
        self.lora_a = Tensor.from_numpy(
            np.random.randn(in_features, self.lora_config.rank).astype(np.float32) * 0.01,
            dtype=self.weight.dtype,
        )
        self.lora_b = Tensor.from_numpy(
            np.zeros((self.lora_config.rank, out_features), dtype=np.float32),
            dtype=self.weight.dtype,
        )
        self.scaling = self.lora_config.alpha / max(1, self.lora_config.rank)

    def forward(self, x: Tensor) -> Tensor:
        base = super().forward(x)
        if self.lora_config.rank <= 0:
            return base
        lora = x @ self.lora_a @ self.lora_b * self.scale()
        return base + lora

    def scale(self) -> float:
        return self.scaling


class QLoRALinear(LoRALinear):
    """Quantized LoRA linear layer for memory-efficient fine-tuning."""

    def __init__(self, in_features: int, out_features: int, config: LoRAConfig | None = None, bias: bool = True) -> None:
        super().__init__(in_features, out_features, config=config, bias=bias)
        self.weight = self._quantize(self.weight)
        self.lora_b = self._quantize(self.lora_b)

    @staticmethod
    def _quantize(tensor: Tensor) -> Tensor:
        array = tensor.numpy().astype(np.int8)
        scale = float(np.max(np.abs(tensor.numpy())))
        if scale == 0:
            scale = 1.0
        quantized = (tensor.numpy() / scale).astype(np.int8)
        return Tensor.from_numpy(quantized, tensor.dtype, tensor.device)

    def dequantize(self, tensor: Tensor) -> Tensor:
        scale = float(np.max(np.abs(tensor.numpy())))
        if scale == 0:
            scale = 1.0
        return Tensor.from_numpy(tensor.numpy().astype(np.float32) * scale, tensor.dtype, tensor.device)
