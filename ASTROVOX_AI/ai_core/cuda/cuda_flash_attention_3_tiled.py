from typing import Optional
import torch
import torch.nn as nn
import torch.nn.functional as F
import math


class FlashAttention3TiledKernel:
    def __init__(self, hidden_size: int, num_heads: int, block_size_m: int = 64, block_size_n: int = 64, use_triton: bool = True):
        self.hidden_size = hidden_size
        self.num_heads = num_heads
        self.head_dim = hidden_size // num_heads
        self.scale = self.head_dim ** -0.5
        self.block_size_m = block_size_m
        self.block_size_n = block_size_n
        self.use_triton = use_triton

    def forward(self, q: torch.Tensor, k: torch.Tensor, v: torch.Tensor, mask: Optional[torch.Tensor] = None, causal: bool = True) -> torch.Tensor:
        B, H, T, D = q.shape
        out = torch.zeros_like(q)
        for start_m in range(0, T, self.block_size_m):
            end_m = min(start_m + self.block_size_m, T)
            q_block = q[:, :, start_m:end_m, :]
            acc = torch.zeros(B, H, end_m - start_m, D, device=q.device, dtype=q.dtype)
            max_stats = torch.full((B, H, end_m - start_m), float('-inf'), device=q.device, dtype=q.dtype)
            sum_stats = torch.zeros(B, H, end_m - start_m, device=q.device, dtype=q.dtype)
            for start_n in range(0, T, self.block_size_n):
                end_n = min(start_n + self.block_size_n, T)
                k_block = k[:, :, start_n:end_n, :]
                v_block = v[:, :, start_n:end_n, :]
                attn_weights = torch.matmul(q_block, k_block.transpose(-2, -1)) * self.scale
                if causal:
                    causal_mask = torch.triu(torch.ones(end_m - start_m, end_n - start_n, device=q.device, dtype=torch.bool), diagonal=(start_n - start_m + 1))
                    attn_weights = attn_weights.masked_fill(causal_mask.unsqueeze(0).unsqueeze(0), float('-inf'))
                if mask is not None:
                    mask_block = mask[..., start_m:end_m, start_n:end_n]
                    attn_weights = attn_weights.masked_fill(mask_block == 0, float('-inf'))
                block_max = attn_weights.max(dim=-1)[0]
                block_max = torch.where(torch.isfinite(block_max), block_max, torch.zeros_like(block_max))
                corrected_max = torch.maximum(max_stats, block_max)
                exp_old = torch.exp(max_stats - corrected_max)
                exp_new = torch.exp(block_max - corrected_max)
                attn_weights = torch.exp(attn_weights - corrected_max.unsqueeze(-1))
                block_sum = attn_weights.sum(dim=-1)
                sum_stats = exp_old * sum_stats + exp_new * block_sum
                acc = exp_old.unsqueeze(-1) * acc + torch.matmul(attn_weights, v_block)
                max_stats = corrected_max
            out[:, :, start_m:end_m, :] = acc / sum_stats.unsqueeze(-1)
        return out


class FlashAttention3Tiled(nn.Module):
    def __init__(self, hidden_size: int, num_heads: int, block_size_m: int = 64, block_size_n: int = 64, use_triton: bool = True):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_heads = num_heads
        self.head_dim = hidden_size // num_heads
        self.scale = self.head_dim ** -0.5
        self.block_size_m = block_size_m
        self.block_size_n = block_size_n
        self.use_triton = use_triton
        self.q_proj = nn.Linear(hidden_size, hidden_size)
        self.k_proj = nn.Linear(hidden_size, hidden_size)
        self.v_proj = nn.Linear(hidden_size, hidden_size)
        self.out_proj = nn.Linear(hidden_size, hidden_size)
        self.tiled_kernel = FlashAttention3TiledKernel(hidden_size, num_heads, block_size_m, block_size_n, use_triton)

    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        B, T, C = x.shape
        q = self.q_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        out = self.tiled_kernel(q, k, v, mask, causal=True)
        out = out.transpose(1, 2).contiguous().view(B, T, C)
        return self.out_proj(out)
