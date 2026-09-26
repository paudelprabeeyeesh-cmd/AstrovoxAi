import logging
from typing import Optional
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
