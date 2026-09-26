import logging
from typing import Optional
import torch
import torch.nn as nn
import math

logger = logging.getLogger(__name__)


class StateSpaceModel(nn.Module):
    def __init__(self, d_state: int = 16, d_conv: int = 4, expand: int = 2, dt_min: float = 0.001, dt_max: float = 0.1):
        super().__init__()
        self.d_state = d_state
        self.d_conv = d_conv
        self.expand = expand
        self.dt_min = dt_min
        self.dt_max = dt_max
        self.in_proj = nn.Linear(d_state, d_state * expand * 2, bias=False)
        self.conv1d = nn.Conv1d(d_state * expand, d_state * expand, d_conv, groups=d_state * expand, padding=d_conv - 1)
        self.act = nn.SiLU()
        self.out_proj = nn.Linear(d_state * expand, d_state, bias=False)
        self.log_dt = nn.Parameter(torch.randn(d_state * expand))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, L, D = x.shape
        x_proj = self.in_proj(x)
        x_proj = x_proj.transpose(1, 2)
        x_conv = self.conv1d(x_proj)[:, :, :L]
        x_conv = self.act(x_conv)
        x_out = self.out_proj(x_conv.transpose(1, 2))
        return x_out
