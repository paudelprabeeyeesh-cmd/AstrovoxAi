from typing import Optional, Dict, Any
import torch
import torch.nn as nn


class FP8Quantizer:
    def __init__(self, format: str = 'E4M3'):
        self.format = format
        self.scales: Dict[str, float] = {}
        if format == 'E4M3':
            self.max_val = 448.0
            self.min_val = -448.0
        else:
            self.max_val = 57344.0
            self.min_val = -57344.0

    def quantize(self, x: torch.Tensor, name: str) -> torch.Tensor:
        scale = self.max_val / x.abs().max().clamp(min=1e-8)
        self.scales[name] = scale.item()
        x_scaled = x * scale
        x_clipped = torch.clamp(x_scaled, self.min_val, self.max_val)
        if self.format == 'E4M3':
            x_fp8 = self._float_to_fp8_e4m3(x_clipped)
        else:
            x_fp8 = self._float_to_fp8_e5m2(x_clipped)
        return x_fp8

    def dequantize(self, x_fp8: torch.Tensor, name: str) -> torch.Tensor:
        scale = self.scales.get(name, 1.0)
        if self.format == 'E4M3':
            x = self._fp8_e4m3_to_float(x_fp8)
        else:
            x = self._fp8_e5m2_to_float(x_fp8)
        return x / scale

    def _float_to_fp8_e4m3(self, x: torch.Tensor) -> torch.Tensor:
        return (x / 16.0).clamp(-14, 14).to(torch.int8)

    def _fp8_e4m3_to_float(self, x: torch.Tensor) -> torch.Tensor:
        return x.float() * 16.0

    def _float_to_fp8_e5m2(self, x: torch.Tensor) -> torch.Tensor:
        return (x / 512.0).clamp(-240, 240).to(torch.int8)

    def _fp8_e5m2_to_float(self, x: torch.Tensor) -> torch.Tensor:
        return x.float() * 512.0
