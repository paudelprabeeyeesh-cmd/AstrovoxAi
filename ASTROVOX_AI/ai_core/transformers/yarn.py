from typing import Optional
import torch
import torch.nn as nn
import math


class YaRN(nn.Module):
    def __init__(self, dim: int, max_seq_len: int, scale: float = 1.0, alpha: float = 1.0, beta: float = 1.0):
        super().__init__()
        self.dim = dim
        self.max_seq_len = max_seq_len
        self.scale = scale
        self.alpha = alpha
        self.beta = beta
        self.register_buffer('inv_freq', 1.0 / (10000.0 ** (torch.arange(0, dim, 2).float() / dim)), persistent=False)

    def forward(self, x: torch.Tensor, seq_len: Optional[int] = None) -> torch.Tensor:
        if seq_len is None:
            seq_len = x.shape[-2]
        t = torch.arange(seq_len, device=x.device).type_as(self.inv_freq) / self.scale
        freqs = torch.outer(t, self.inv_freq)
        freq_extra = freqs / self.alpha
        freq_regular = freqs / self.scale
        freq_extra = freq_extra % (2 * math.pi)
        freq_regular = freq_regular % (2 * math.pi)
        emb = torch.cat((freq_extra.sin(), freq_regular.cos()), dim=-1)
        x1, x2 = x[..., ::2], x[..., 1::2]
        x_rotated = torch.stack((-x2, x1), dim=-1).flatten(-2)
        return x * emb.unsqueeze(0).unsqueeze(0) + x_rotated * emb.unsqueeze(0).unsqueeze(0)
