import logging
from typing import Optional, Tuple
import torch
import torch.nn as nn
import math

logger = logging.getLogger(__name__)


class RoPE(nn.Module):
    def __init__(self, hidden_size: int, num_heads: int, max_seq_len: int = 2048, base: float = 10000.0):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_heads = num_heads
        self.max_seq_len = max_seq_len
        self.base = base
        self.head_dim = hidden_size // num_heads
        self.inv_freq = 1.0 / (base ** (torch.arange(0, self.head_dim, 2).float() / self.head_dim))
        self._build_cache(max_seq_len)

    def _build_cache(self, seq_len: int):
        t = torch.arange(seq_len, device=self.inv_freq.device).type_as(self.inv_freq)
        freqs = torch.outer(t, self.inv_freq)
        emb = torch.cat([freqs, freqs], dim=-1)
        self.register_buffer("cos_cached", emb.cos().unsqueeze(0).unsqueeze(0), persistent=False)
        self.register_buffer("sin_cached", emb.sin().unsqueeze(0).unsqueeze(0), persistent=False)

    def forward(self, q: torch.Tensor, k: torch.Tensor, seq_len: Optional[int] = None) -> Tuple[torch.Tensor, torch.Tensor]:
        if seq_len is None:
            seq_len = q.shape[-2]
        if seq_len > self.max_seq_len:
            self._build_cache(seq_len)
        cos = self.cos_cached[:, :, :seq_len, :self.head_dim]
        sin = self.sin_cached[:, :, :seq_len, :self.head_dim]
        q_embed = (q * cos) + (self._rotate_half(q) * sin)
        k_embed = (k * cos) + (self._rotate_half(k) * sin)
        return q_embed, k_embed

    def _rotate_half(self, x: torch.Tensor) -> torch.Tensor:
        x1 = x[..., : x.shape[-1] // 2]
        x2 = x[..., x.shape[-1] // 2 :]
        return torch.cat((-x2, x1), dim=-1)
