from typing import Optional, List, Dict, Any, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F
import math


class FlashAttention3TiledKernel:
    def __init__(self, hidden_size: int, num_heads: int, block_size_m: int = 64, block_size_n: int = 64):
        self.hidden_size = hidden_size
        self.num_heads = num_heads
        self.head_dim = hidden_size // num_heads
        self.scale = self.head_dim ** -0.5
        self.block_size_m = block_size_m
        self.block_size_n = block_size_n

    def forward(self, q: torch.Tensor, k: torch.Tensor, v: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        B, H, T, D = q.shape
        out = torch.zeros_like(q)
        for start_m in range(0, T, self.block_size_m):
            end_m = min(start_m + self.block_size_m, T)
            q_block = q[:, :, start_m:end_m, :]
            acc = torch.zeros(B, H, end_m - start_m, D, device=q.device, dtype=q.dtype)
            for start_n in range(0, T, self.block_size_n):
                end_n = min(start_n + self.block_size_n, T)
                k_block = k[:, :, start_n:end_n, :]
                v_block = v[:, :, start_n:end_n, :]
                attn_weights = torch.matmul(q_block, k_block.transpose(-2, -1)) * self.scale
                if mask is not None:
                    mask_block = mask[..., start_m:end_m, start_n:end_n]
                    attn_weights = attn_weights.masked_fill(mask_block == 0, float('-inf'))
                attn_weights = torch.softmax(attn_weights, dim=-1)
                acc = acc + torch.matmul(attn_weights, v_block)
            out[:, :, start_m:end_m, :] = acc
        return out
