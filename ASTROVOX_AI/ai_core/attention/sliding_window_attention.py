from typing import Optional
import torch
import torch.nn as nn


class SlidingWindowAttention(nn.Module):
    def __init__(self, hidden_size: int, num_heads: int, window_size: int = 512, dropout: float = 0.0):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_heads = num_heads
        self.head_dim = hidden_size // num_heads
        self.window_size = window_size
        self.scale = self.head_dim ** -0.5
        self.q_proj = nn.Linear(hidden_size, hidden_size)
        self.k_proj = nn.Linear(hidden_size, hidden_size)
        self.v_proj = nn.Linear(hidden_size, hidden_size)
        self.out_proj = nn.Linear(hidden_size, hidden_size)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        B, T, C = x.shape
        q = self.q_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        window_mask = torch.zeros(T, T, device=x.device, dtype=torch.bool)
        for i in range(T):
            start = max(0, i - self.window_size)
            end = min(T, i + self.window_size + 1)
            window_mask[i, start:end] = True
        attn = (q @ k.transpose(-2, -1)) * self.scale
        attn = attn.masked_fill(~window_mask.unsqueeze(0).unsqueeze(0), float('-inf'))
        attn = attn.softmax(dim=-1)
        attn = self.dropout(attn)
        out = attn @ v
        out = out.transpose(1, 2).contiguous().view(B, T, C)
        return self.out_proj(out)
