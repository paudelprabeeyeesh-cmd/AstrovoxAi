import logging
from typing import Optional, Tuple
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


class KVCompression(nn.Module):
    def __init__(self, hidden_size: int, num_heads: int, compression_factor: int = 2):
        super().__init__()
        self.num_heads = num_heads
        self.head_dim = hidden_size // num_heads
        self.compression_factor = compression_factor
        self.k_compress = nn.Linear(hidden_size, hidden_size // compression_factor, bias=False)
        self.v_compress = nn.Linear(hidden_size, hidden_size // compression_factor, bias=False)

    def forward(self, k: torch.Tensor, v: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        B, H, T, D = k.shape
        k_compressed = self.k_compress(k.transpose(1, 2).contiguous().view(B, T, -1))
        v_compressed = self.v_compress(v.transpose(1, 2).contiguous().view(B, T, -1))
        new_D = self.head_dim // self.compression_factor
        k_compressed = k_compressed.view(B, T, H, new_D).transpose(1, 2)
        v_compressed = v_compressed.view(B, T, H, new_D).transpose(1, 2)
        return k_compressed, v_compressed


class KVCompressedAttention(nn.Module):
    def __init__(self, hidden_size: int, num_heads: int, compression_factor: int = 2, dropout: float = 0.0):
        super().__init__()
        self.num_heads = num_heads
        self.head_dim = hidden_size // num_heads
        self.compressed_dim = self.head_dim // compression_factor
        self.scale = self.compressed_dim ** -0.5
        self.q_proj = nn.Linear(hidden_size, self.compressed_dim * num_heads)
        self.kv_compress = KVCompression(hidden_size, num_heads, compression_factor)
        self.out_proj = nn.Linear(self.compressed_dim * num_heads, hidden_size)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        B, T, C = x.shape
        q = self.q_proj(x).view(B, T, self.num_heads, self.compressed_dim).transpose(1, 2)
        k = self.q_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        v = self.q_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        k, v = self.kv_compress(k, v)
        attn = (q @ k.transpose(-2, -1)) * self.scale
        if mask is not None:
            attn = attn.masked_fill(mask == 0, float('-inf'))
        attn = attn.softmax(dim=-1)
        attn = self.dropout(attn)
        out = attn @ v
        out = out.transpose(1, 2).contiguous().view(B, T, self.compressed_dim * self.num_heads)
        return self.out_proj(out)
