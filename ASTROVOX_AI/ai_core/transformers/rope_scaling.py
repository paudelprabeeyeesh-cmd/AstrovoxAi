from typing import Optional
import torch
import torch.nn as nn


class RoPE(nn.Module):
    def __init__(self, dim: int, max_seq_len: int = 2048, base: float = 10000.0):
        super().__init__()
        self.dim = dim
        self.max_seq_len = max_seq_len
        self.base = base
        self.register_buffer('inv_freq', 1.0 / (base ** (torch.arange(0, dim, 2).float() / dim)), persistent=False)

    def forward(self, x: torch.Tensor, seq_len: Optional[int] = None) -> torch.Tensor:
        if seq_len is None:
            seq_len = x.shape[-2]
        t = torch.arange(seq_len, device=x.device).type_as(self.inv_freq)
        freqs = torch.outer(t, self.inv_freq)
        emb = torch.cat((freqs.sin(), freqs.cos()), dim=-1)
        x1, x2 = x[..., ::2], x[..., 1::2]
        x_rotated = torch.stack((-x2, x1), dim=-1).flatten(-2)
        return x * emb.unsqueeze(0).unsqueeze(0) + x_rotated * emb.unsqueeze(0).unsqueeze(0)


class RoPEScaling(nn.Module):
    def __init__(self, dim: int, scale: float = 1.0, max_seq_len: int = 2048):
        super().__init__()
        self.dim = dim
        self.scale = scale
        self.max_seq_len = max_seq_len
        self.rope = RoPE(dim, max_seq_len)

    def forward(self, x: torch.Tensor, seq_len: Optional[int] = None) -> torch.Tensor:
        return self.rope(x * self.scale, seq_len)
