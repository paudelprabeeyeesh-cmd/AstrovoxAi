from typing import Optional, Dict, Any
import torch
import torch.nn as nn
import logging

logger = logging.getLogger(__name__)


class INT4Quantizer:
    def __init__(self, group_size: int = 128, bits: int = 4):
        self.group_size = group_size
        self.bits = bits
        self.scales: Dict[str, Any] = {}

    def quantize(self, model: nn.Module) -> nn.Module:
        for name, module in model.named_modules():
            if isinstance(module, nn.Linear):
                weight = module.weight.data
                out_dim, in_dim = weight.shape
                scales = []
                qweight = []
                for i in range(0, in_dim, self.group_size):
                    block = weight[:, i:i + self.group_size]
                    scale = block.abs().max(dim=1, keepdim=True).values / 7.0
                    scales.append(scale)
                    qblock = (block / scale).round().clamp(-8, 7).to(torch.int8)
                    qweight.append(qblock)
                self.scales[name + '.weight'] = torch.cat(scales, dim=1)
                module.weight.data = torch.cat(qweight, dim=1).to(torch.int8)
        return model

    def quantize_activation(self, x: torch.Tensor, key: str) -> torch.Tensor:
        scale = self.scales.get(key, x.abs().max() / 7.0)
        return (x / scale).round().clamp(-8, 7).to(torch.int8).float() * scale

    def dequantize(self, qweight: torch.Tensor, scales: torch.Tensor) -> torch.Tensor:
        return qweight.float() * scales
