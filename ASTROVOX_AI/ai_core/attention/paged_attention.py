from typing import Optional
import torch
import torch.nn as nn


class PagedAttention(nn.Module):
    def __init__(self, hidden_size: int, num_heads: int, block_size: int = 16, num_kv_heads: Optional[int] = None, dropout: float = 0.0):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_heads = num_heads
        self.num_kv_heads = num_kv_heads if num_kv_heads is not None else num_heads
        self.head_dim = hidden_size // num_heads
        self.block_size = block_size
        self.scale = self.head_dim ** -0.5
        self.q_proj = nn.Linear(hidden_size, num_heads * self.head_dim)
        self.k_proj = nn.Linear(hidden_size, self.num_kv_heads * self.head_dim)
        self.v_proj = nn.Linear(hidden_size, self.num_kv_heads * self.head_dim)
        self.out_proj = nn.Linear(num_heads * self.head_dim, hidden_size)
        self.dropout = nn.Dropout(dropout)
        self.num_key_value_groups = num_heads // self.num_kv_heads

    def forward(self, x: torch.Tensor, k_cache: Optional[torch.Tensor] = None, v_cache: Optional[torch.Tensor] = None, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        B, T, C = x.shape
        q = self.q_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(B, T, self.num_kv_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(B, T, self.num_kv_heads, self.head_dim).transpose(1, 2)
        if k_cache is not None:
            k = torch.cat([k_cache, k], dim=2)
            v = torch.cat([v_cache, v], dim=2)
        if self.num_key_value_groups > 1:
            k = k.repeat_interleave(self.num_key_value_groups, dim=1)
            v = v.repeat_interleave(self.num_key_value_groups, dim=1)
        attn = (q @ k.transpose(-2, -1)) * self.scale
        if mask is not None:
            attn = attn.masked_fill(mask == 0, float('-inf'))
        attn = attn.softmax(dim=-1)
        attn = self.dropout(attn)
        out = attn @ v
        out = out.transpose(1, 2).contiguous().view(B, T, C)
        return self.out_proj(out)
