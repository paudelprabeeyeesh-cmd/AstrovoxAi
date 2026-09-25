from typing import Optional, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F


class FlashAttention3(nn.Module):
    def __init__(self, hidden_size: int, num_heads: int, dropout: float = 0.0, use_custom_kernel: bool = False):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_heads = num_heads
        self.head_dim = hidden_size // num_heads
        self.scale = self.head_dim ** -0.5
        self.q_proj = nn.Linear(hidden_size, hidden_size)
        self.k_proj = nn.Linear(hidden_size, hidden_size)
        self.v_proj = nn.Linear(hidden_size, hidden_size)
        self.out_proj = nn.Linear(hidden_size, hidden_size)
        self.dropout = nn.Dropout(dropout)
        self.use_custom_kernel = use_custom_kernel

    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        B, T, C = x.shape
        q = self.q_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        if self.use_custom_kernel:
            try:
                from ASTROVOX_AI.ai_core.cuda.cuda_flash_attention_3 import flash_attention_3_forward
                out = flash_attention_3_forward(q, k, v, dropout_p=self.dropout.p, causal=True)
                return self.out_proj(out.view(B, T, C))
            except ImportError:
                pass
        attn = (q @ k.transpose(-2, -1)) * self.scale
        if mask is not None:
            attn = attn.masked_fill(mask == 0, float('-inf'))
        attn = attn.softmax(dim=-1)
        attn = self.dropout(attn)
        out = attn @ v
        out = out.transpose(1, 2).contiguous().view(B, T, C)
        return self.out_proj(out)
