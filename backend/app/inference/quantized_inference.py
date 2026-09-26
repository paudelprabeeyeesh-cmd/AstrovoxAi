"""Quantized inference service wrapper."""

from __future__ import annotations

import logging
from typing import Optional

import torch
import torch.nn as nn

from ASTROVOX_AI.ai_core.inference.quantized_inference import QuantizedInferenceEngine, QuantizedInferenceConfig

logger = logging.getLogger(__name__)


class QuantizedInferenceService:
    def __init__(self, model: nn.Module, weight_bits: int = 8, activation_bits: int = 8, quant_method: str = "dynamic"):
        self.config = QuantizedInferenceConfig(
            weight_bits=weight_bits,
            activation_bits=activation_bits,
            quant_method=quant_method,
        )
        self.engine = QuantizedInferenceEngine(model, self.config)

    def quantize(self) -> nn.Module:
        return self.engine.quantize()

    def benchmark(self, sample: torch.Tensor, warmup: int = 10, repeat: int = 50) -> dict:
        return self.engine.benchmark(sample, warmup=warmup, repeat=repeat)

    def export(self, path: str) -> None:
        self.engine.export(path)
