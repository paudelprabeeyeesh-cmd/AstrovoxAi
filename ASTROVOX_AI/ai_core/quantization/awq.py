from typing import Optional, Dict, Any, List
import torch
import torch.nn as nn


class AWQQuantizer:
    def __init__(self, bits: int = 4, group_size: int = 128, zero_point: bool = True):
        self.bits = bits
        self.group_size = group_size
        self.zero_point = zero_point
        self.scales: Dict[str, torch.Tensor] = {}
        self.zero_points: Dict[str, torch.Tensor] = {}

    def quantize_weight(self, weight: torch.Tensor, name: str) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        weight = weight.float()
        out_features, in_features = weight.shape
        max_q = 2 ** self.bits - 1
        scales = torch.zeros(out_features, dtype=torch.float32)
        zeros = torch.zeros(out_features, dtype=torch.float32) if self.zero_point else None
        q_weight = torch.zeros_like(weight, dtype=torch.int32)
        for i in range(0, in_features, self.group_size):
            block = weight[:, i:i + self.group_size]
            w_min, w_max = block.min(dim=1)[0], block.max(dim=1)[0]
            if self.zero_point:
                scale = (w_max - w_min) / max_q
                scale = torch.clamp(scale, min=1e-8)
                zero = torch.round(-w_min / scale)
                q_block = (block / scale.unsqueeze(1) + zero.unsqueeze(1)).round().clamp(0, max_q)
                zeros[i:i + self.group_size] = zero
            else:
                scale = w_max / max_q
                scale = torch.clamp(scale, min=1e-8)
                q_block = (block / scale.unsqueeze(1)).round().clamp(0, max_q)
            q_weight[:, i:i + self.group_size] = q_block
            scales[i:i + self.group_size] = scale
        self.scales[name] = scales
        if self.zero_point:
            self.zero_points[name] = zeros
        return q_weight.float(), scales, zeros

    def quantize_model(self, model: nn.Module) -> nn.Module:
        for name, module in model.named_modules():
            if isinstance(module, nn.Linear):
                q_weight, scale, _ = self.quantize_weight(module.weight.data, name)
                module.weight.data = q_weight
                self.scales[name] = scale
        return model
