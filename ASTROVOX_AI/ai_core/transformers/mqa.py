from typing import Optional, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F


class MultiQueryAttention(nn.Module):
    def __init__(self, hidden_size: int, num_heads: int, dropout: float = 0.0):
        super().__init__()
        assert hidden_size % num_heads == 0
        self.hidden_size = hidden_size
        self.num_heads = num_heads
        self.head_dim = hidden_size // num_heads
        self.scale = self.head_dim ** -0.5
        self.q_proj = nn.Linear(hidden_size, num_heads * self.head_dim)
        self.k_proj = nn.Linear(hidden_size, self.head_dim)
        self.v_proj = nn.Linear(hidden_size, self.head_dim)
        self.out_proj = nn.Linear(num_heads * self.head_dim, hidden_size)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        B, T, C = x.shape
        q = self.q_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(B, T, 1, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(B, T, 1, self.head_dim).transpose(1, 2)
        k = k.repeat_interleave(self.num_heads, dim=1)
        v = v.repeat_interleave(self.num_heads, dim=1)
        attn = (q @ k.transpose(-2, -1)) * self.scale
        if mask is not None:
            attn = attn.masked_fill(mask == 0, float('-inf'))
        attn = attn.softmax(dim=-1)
        attn = self.dropout(attn)
        out = attn @ v
        out = out.transpose(1, 2).contiguous().view(B, T, C)
        return self.out_proj(out)


class MQABlock(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.attn = MultiQueryAttention(config.hidden_size, config.num_heads, config.dropout)
        self.ffn = FeedForward(config)
        self.ln1 = nn.LayerNorm(config.hidden_size)
        self.ln2 = nn.LayerNorm(config.hidden_size)
        self.dropout = nn.Dropout(config.dropout)

    def forward(self, x, mask=None):
        x = x + self.dropout(self.attn(self.ln1(x), mask))
        x = x + self.dropout(self.ffn(self.ln2(x)))
        return x
