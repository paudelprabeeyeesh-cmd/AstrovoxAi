import logging
from typing import Optional
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


class ALiBi(nn.Module):
    def __init__(self, num_heads: int, max_seq_len: int = 2048):
        super().__init__()
        self.num_heads = num_heads
        self.max_seq_len = max_seq_len
        slopes = torch.tensor([2 ** (-8 * (i + 1) / num_heads) for i in range(num_heads)])
        self.register_buffer('slopes', slopes, persistent=False)
        self.register_buffer('bias', self._build_bias(max_seq_len), persistent=False)

    def _build_bias(self, max_seq_len: int) -> torch.Tensor:
        context = torch.arange(max_seq_len, dtype=torch.float32).unsqueeze(0) - torch.arange(max_seq_len, dtype=torch.float32).unsqueeze(1)
        bias = -torch.abs(context).unsqueeze(0).unsqueeze(0)
        return bias

    def forward(self, attn: torch.Tensor, seq_len: Optional[int] = None) -> torch.Tensor:
        if seq_len is None:
            seq_len = attn.shape[-1]
        return attn + self.bias[:, :, :seq_len, :seq_len] * self.slopes.view(-1, 1, 1, 1)


class ALiBiAttention(nn.Module):
    def __init__(self, hidden_size: int, num_heads: int, dropout: float = 0.1):
        super().__init__()
        self.num_heads = num_heads
        self.head_dim = hidden_size // num_heads
        self.scale = self.head_dim ** -0.5
        self.q_proj = nn.Linear(hidden_size, hidden_size)
        self.k_proj = nn.Linear(hidden_size, hidden_size)
        self.v_proj = nn.Linear(hidden_size, hidden_size)
        self.out_proj = nn.Linear(hidden_size, hidden_size)
        self.alibi = ALiBi(num_heads)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        B, T, C = x.shape
        q = self.q_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        attn = (q @ k.transpose(-2, -1)) * self.scale
        attn = self.alibi(attn, T)
        if mask is not None:
            attn = attn.masked_fill(mask == 0, float('-inf'))
        attn = attn.softmax(dim=-1)
        attn = self.dropout(attn)
        out = attn @ v
        out = out.transpose(1, 2).contiguous().view(B, T, C)
        return self.out_proj(out)
