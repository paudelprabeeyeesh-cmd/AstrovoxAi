from typing import Optional, Dict, Any, Tuple
import torch
import torch.nn as nn


class NF4Quantizer:
    def __init__(self, block_size: int = 64, offset: float = 0.9677):
        self.block_size = block_size
        self.offset = offset
        self.scales: Dict[str, torch.Tensor] = {}

    def _quantize_block(self, block: torch.Tensor) -> Tuple[torch.Tensor, float]:
        block_flat = block.float().flatten()
        absmax = block_flat.abs().max().clamp(min=1e-8)
        scale = absmax / self.offset
        normalized = block_flat / scale
        nf4_codes = self._float_to_nf4(normalized)
        return nf4_codes.view_as(block), scale.item()

    def _float_to_nf4(self, x: torch.Tensor) -> torch.Tensor:
        nf4_map = torch.tensor([
            -1.0, -0.6961928009986877, -0.5250730514526367, -0.39491748809814453,
            -0.28444138169288635, -0.18477343022823334, -0.09105003625154495, 0.0,
            0.07958029955625534, 0.16093020141124725, 0.2461123007736206, 0.33791524171829224,
            0.44070982933044434, 0.5626170039176941, 0.7229568360891342, 1.0
        ], device=x.device)
        x_expanded = x.unsqueeze(-1)
        idx = (x_expanded - nf4_map).abs().argmin(dim=-1)
        return idx.to(torch.uint8)

    def _nf4_to_float(self, codes: torch.Tensor, scale: float) -> torch.Tensor:
        nf4_map = torch.tensor([
            -1.0, -0.6961928009986877, -0.5250730514526367, -0.39491748809814453,
            -0.28444138169288635, -0.18477343022823334, -0.09105003625154495, 0.0,
            0.07958029955625534, 0.16093020141124725, 0.2461123007736206, 0.33791524171829224,
            0.44070982933044434, 0.5626170039176941, 0.7229568360891342, 1.0
        ], device=codes.device)
        return nf4_map[codes.long()] * scale

    def quantize_weight(self, weight: torch.Tensor, name: str) -> Tuple[torch.Tensor, torch.Tensor]:
        out_features, in_features = weight.shape
        q_blocks = []
        scales = []
        for i in range(0, in_features, self.block_size):
            block = weight[:, i:i + self.block_size]
            q_block, scale = self._quantize_block(block)
            q_blocks.append(q_block)
            scales.append(scale)
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
            dequant[:, i:i + self.block_size] = self._nf4_to_float(q_weight[:, i:i + self.block_size], scale)
        return dequant
