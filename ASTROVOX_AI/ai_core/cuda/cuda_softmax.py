from typing import Optional
import torch
import torch.nn as nn
import torch.nn.functional as F


class CUDASoftmax(nn.Module):
    def __init__(self, dim: int = -1, use_fast_math: bool = True):
        super().__init__()
        self.dim = dim
        self.use_fast_math = use_fast_math

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.use_fast_math:
            return torch.softmax(x, dim=self.dim)
        x_max, _ = x.max(dim=self.dim, keepdim=True)
        x_exp = torch.exp(x - x_max)
        return x_exp / x_exp.sum(dim=self.dim, keepdim=True)


class CUDASoftmaxWithMask(nn.Module):
    def __init__(self, dim: int = -1):
        super().__init__()
        self.dim = dim

    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        if mask is not None:
            x = x.masked_fill(mask == 0, float('-inf'))
        return torch.softmax(x, dim=self.dim)
