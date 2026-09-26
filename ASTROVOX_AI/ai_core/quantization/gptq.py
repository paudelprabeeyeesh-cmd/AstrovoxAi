from typing import Dict
import torch
import torch.nn as nn


class GPTQQuantizer:
    def __init__(self, bits: int = 4, group_size: int = 128, actorder: bool = True):
        self.bits = bits
        self.group_size = group_size
        self.actorder = actorder
        self.scales: Dict[str, torch.Tensor] = {}
        self.zeros: Dict[str, torch.Tensor] = {}

    def quantize_weight(self, weight: torch.Tensor, name: str) -> Tuple[torch.Tensor, torch.Tensor]:
        out_features, in_features = weight.shape
        weight = weight.float()
        max_q = 2 ** self.bits - 1
        scales = torch.zeros(out_features, dtype=torch.float32)
        zeros = torch.zeros(out_features, dtype=torch.float32)
        q_weight = torch.zeros_like(weight, dtype=torch.int32)
        for i in range(0, in_features, self.group_size):
            block = weight[:, i:i + self.group_size]
            block_max = block.abs().max(dim=1)[0]
            scale = block_max / max_q
            scale = torch.clamp(scale, min=1e-8)
            zero = torch.zeros_like(scale)
            q_block = (block / scale.unsqueeze(1)).round().clamp(0, max_q)
            q_weight[:, i:i + self.group_size] = q_block
            scales[i:i + self.group_size] = scale
            zeros[i:i + self.group_size] = zero
        self.scales[name] = scales
        self.zeros[name] = zeros
        return q_weight.float(), scales

    def quantize_model(self, model: nn.Module) -> nn.Module:
        for name, module in model.named_modules():
            if isinstance(module, nn.Linear):
                q_weight, scale = self.quantize_weight(module.weight.data, name)
                module.weight.data = q_weight
                self.scales[name] = scale
        return model

    def dequantize(self, q_weight: torch.Tensor, scale: torch.Tensor) -> torch.Tensor:
        return q_weight * scale.unsqueeze(1)
