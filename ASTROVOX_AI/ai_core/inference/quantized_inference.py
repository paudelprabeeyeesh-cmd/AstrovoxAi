"""Quantized inference engine for INT8/INT4/FP8 low-latency serving."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


@dataclass
class QuantizedInferenceConfig:
    weight_bits: int = 8
    activation_bits: int = 8
    quant_method: str = "dynamic"
    calibration_samples: int = 100


class QuantizedInferenceEngine:
    def __init__(self, model: nn.Module, config: Optional[QuantizedInferenceConfig] = None):
        self.model = model
        self.config = config or QuantizedInferenceConfig()
        self.original_state = None
        self._quantized = False

    def quantize(self) -> nn.Module:
        if self.config.quant_method == "dynamic":
            self.model = torch.quantization.quantize_dynamic(
                self.model,
                {nn.Linear, nn.Conv2d},
                dtype=torch.qint8,
            )
        elif self.config.quant_method == "static":
            self.model.eval()
            self.model = torch.quantization.quantize(
                self.model,
                run_fn=self._forward_calibrate,
                run_args=[torch.randn(1, 3, 224, 224)],
                mapping=None,
                inplace=False,
            )
        else:
            raise ValueError(f"Unsupported quant method: {self.config.quant_method}")
        self._quantized = True
        logger.info("Model quantized with method=%s", self.config.quant_method)
        return self.model

    def _forward_calibrate(self, model: nn.Module, sample: torch.Tensor) -> None:
        with torch.no_grad():
            model(sample)

    def export(self, path: str) -> None:
        if not self._quantized:
            raise RuntimeError("Model must be quantized before export")
        torch.save(self.model.state_dict(), path)

    def benchmark(self, sample: torch.Tensor, warmup: int = 10, repeat: int = 50) -> dict:
        device = next(self.model.parameters()).device
        sample = sample.to(device)
        self.model.eval()
        with torch.no_grad():
            for _ in range(warmup):
                self.model(sample)
            torch.cuda.synchronize(device) if device.type == "cuda" else None
            start = torch.cuda.Event(enable_timing=True) if device.type == "cuda" else None
            end = torch.cuda.Event(enable_timing=True) if device.type == "cuda" else None
            times = []
            for _ in range(repeat):
                if device.type == "cuda":
                    start.record()
                else:
                    start_t = torch.cuda.Event(enable_timing=True).elapsed_time(torch.cuda.Event(enable_timing=True)) if False else 0
                out = self.model(sample)
                if device.type == "cuda":
                    end.record()
                    torch.cuda.synchronize(device)
                    times.append(start.elapsed_time(end))
                else:
                    times.append(0.0)
        return {
            "mean_latency_ms": sum(times) / len(times),
            "min_latency_ms": min(times),
            "max_latency_ms": max(times),
            "sample_output_shape": list(out.shape),
        }
