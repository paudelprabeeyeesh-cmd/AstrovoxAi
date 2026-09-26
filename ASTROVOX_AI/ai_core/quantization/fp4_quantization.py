from typing import Dict, Tuple
import torch
import torch.nn as nn


class FP4Quantizer:
    def __init__(self, block_size: int = 128, format: str = 'E2M1'):
        self.block_size = block_size
        self.format = format
        self.scales: Dict[str, torch.Tensor] = {}
        if format == 'E2M1':
            self.max_val = 6.0
            self.min_val = -6.0
            self.num_bits = 4
        else:
            self.max_val = 448.0
            self.min_val = -448.0
            self.num_bits = 4

    def _quantize_fp4(self, x: torch.Tensor) -> torch.Tensor:
        x_clipped = torch.clamp(x, self.min_val, self.max_val)
        if self.format == 'E2M1':
            sign = (x_clipped < 0).to(torch.uint8) * 8
            abs_x = x_clipped.abs()
            exp = torch.clamp(torch.floor(torch.log2(abs_x.clamp(min=1e-8))), 0, 3).to(torch.uint8)
            mantissa = torch.clamp(torch.round((abs_x / (2.0 ** exp) - 1.0) * 2), 0, 1).to(torch.uint8)
            return (sign + exp * 2 + mantissa).to(torch.uint8)
        return (x_clipped / 32.0).clamp(-7, 7).to(torch.int8) + 8

    def _dequantize_fp4(self, codes: torch.Tensor) -> torch.Tensor:
        if self.format == 'E2M1':
            sign = (codes & 0x8).to(torch.float32)
            exp = ((codes & 0x6) >> 1).to(torch.float32)
            mantissa = (codes & 0x1).to(torch.float32)
            magnitude = (1.0 + mantissa * 0.5) * (2.0 ** exp)
            return ((-1.0) ** sign) * magnitude
        return (codes.float() - 8.0) * 32.0

    def quantize_weight(self, weight: torch.Tensor, name: str) -> Tuple[torch.Tensor, torch.Tensor]:
        out_features, in_features = weight.shape
        q_blocks = []
        scales = []
        for i in range(0, in_features, self.block_size):
            block = weight[:, i:i + self.block_size].float()
            absmax = block.abs().max().clamp(min=1e-8)
            scale = absmax / self.max_val
            normalized = block / scale
            q_block = self._quantize_fp4(normalized)
            q_blocks.append(q_block)
            scales.append(scale.item())
        q_weight = torch.cat(q_blocks, dim=1)
        self.scales[name] = torch.tensor(scales, device=weight.device)
        return q_weight, self.scales[name]

    def quantize_model(self, model: nn.Module) -> nn.Module:
        for name, module in model.named_modules():
            if isinstance(module, nn.Linear):
                q_weight, _ = self.quantize_weight(module.weight.data, name)
                module.weight.data = q_weight.float()
        return model

    def dequantize(self, q_weight: torch.Tensor, scales: torch.Tensor) -> torch.Tensor:
        out_features, in_features = q_weight.shape
        dequant = torch.zeros_like(q_weight, dtype=torch.float32)
        for i in range(0, in_features, self.block_size):
            block_idx = i // self.block_size
            scale = scales[block_idx]
            dequant[:, i:i + self.block_size] = self._dequantize_fp4(q_weight[:, i:i + self.block_size]) * scale
        return dequant
