from typing import Optional
import torch
import torch.nn as nn


class CUDADequantizedLinear(nn.Module):
    def __init__(self, in_features: int, out_features: int, weight_bits: int = 8, use_triton: bool = True):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.weight_bits = weight_bits
        self.use_triton = use_triton
        self.q_weight = nn.Parameter(torch.zeros(out_features, in_features, dtype=torch.int8))
        self.scale = nn.Parameter(torch.ones(out_features))
        self.zero_point = nn.Parameter(torch.zeros(out_features, dtype=torch.int8))

    def dequantize(self) -> torch.Tensor:
        return (self.q_weight.float() - self.zero_point.unsqueeze(1).float()) * self.scale.unsqueeze(1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        dequant_weight = self.dequantize()
        return torch.nn.functional.linear(x, dequant_weight)


class CUDASmoothQuantLinear(nn.Module):
    def __init__(self, in_features: int, out_features: int, weight_bits: int = 8, alpha: float = 0.5):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.weight_bits = weight_bits
        self.alpha = alpha
        self.scale = nn.Parameter(torch.ones(in_features))
        self.q_weight = nn.Parameter(torch.zeros(out_features, in_features, dtype=torch.int8))
        self.w_scale = nn.Parameter(torch.ones(out_features))

    def smooth_quantize(self, x: torch.Tensor, weight: torch.Tensor) -> tuple:
        act_abs_max = x.abs().max(dim=0)[0]
        weight_abs_max = weight.abs().max(dim=1)[0]
        smooth_scale = (act_abs_max.pow(self.alpha) / weight_abs_max.pow(1 - self.alpha)).clamp(min=1e-5)
        smooth_weight = weight * smooth_scale.unsqueeze(0)
        smooth_x = x / smooth_scale.unsqueeze(0)
        qmin = -(2 ** (self.weight_bits - 1))
        qmax = 2 ** (self.weight_bits - 1) - 1
        scale = (smooth_weight.max(dim=1)[0] - smooth_weight.min(dim=1)[0]) / (qmax - qmin)
        scale = torch.clamp(scale, min=1e-8)
        zp = torch.clamp(-smooth_weight.min(dim=1)[0] / scale, qmin, qmax).round()
        q_weight = ((smooth_weight / scale.unsqueeze(1)) + zp.unsqueeze(1)).round().clamp(qmin, qmax)
        return q_weight, scale, zp, smooth_scale

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        q_weight, scale, zp, smooth_scale = self.smooth_quantize(x, self.weight)
        dequant = ((q_weight.float() - zp.unsqueeze(1)) * scale.unsqueeze(1)) / smooth_scale.unsqueeze(0)
        return torch.nn.functional.linear(x, dequant)


class CUDAAWQDequantizedLinear(nn.Module):
    def __init__(self, in_features: int, out_features: int, group_size: int = 128):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.group_size = group_size
        self.num_groups = in_features // group_size
        self.q_weight = nn.Parameter(torch.zeros(out_features, in_features, dtype=torch.int8))
        self.scales = nn.Parameter(torch.ones(out_features, self.num_groups))
        self.zero_points = nn.Parameter(torch.zeros(out_features, self.num_groups, dtype=torch.int8))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        dequant = ((self.q_weight.float() - self.zero_points.unsqueeze(2).float()) * self.scales.unsqueeze(2)).reshape(self.out_features, self.in_features)
        return torch.nn.functional.linear(x, dequant)
