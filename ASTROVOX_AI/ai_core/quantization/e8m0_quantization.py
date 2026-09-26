from typing import Dict, Tuple
import torch
import torch.nn as nn


class E8M0Quantizer:
    def __init__(self, block_size: int = 128):
        self.block_size = block_size
        self.scales: Dict[str, torch.Tensor] = {}

    def _e8m0_encode(self, x: torch.Tensor) -> torch.Tensor:
        sign = torch.sign(x)
        abs_x = x.abs()
        log2 = torch.log2(abs_x.clamp(min=1e-8))
        exp_bits = torch.clamp(torch.round(log2), 0, 7).to(torch.uint8)
        return (sign > 0).to(torch.uint8) * 128 + exp_bits

    def _e8m0_decode(self, codes: torch.Tensor) -> torch.Tensor:
        exp_bits = codes & 0x7F
        sign = (codes & 0x80).to(torch.float32)
        return ((-1.0) ** sign) * (2.0 ** exp_bits.float())

    def quantize_weight(self, weight: torch.Tensor, name: str) -> Tuple[torch.Tensor, torch.Tensor]:
        out_features, in_features = weight.shape
        q_blocks = []
        scales = []
        for i in range(0, in_features, self.block_size):
            block = weight[:, i:i + self.block_size].float()
            absmax = block.abs().max().clamp(min=1e-8)
            scale = absmax / 127.0
            normalized = block / scale
            q_block = self._e8m0_encode(normalized)
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
            dequant[:, i:i + self.block_size] = self._e8m0_decode(q_weight[:, i:i + self.block_size]) * scale
        return dequant
