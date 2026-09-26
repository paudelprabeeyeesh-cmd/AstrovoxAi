"""FlashAttention v2/v3-style memory-efficient attention implementation."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


@dataclass
class FlashAttentionConfig:
    hidden_size: int
    num_heads: int
    dropout: float = 0.0
    block_size: int = 128
    causal: bool = True
    use_flash_kernel: bool = True
    softmax_scale: Optional[float] = None


@dataclass
class FlashAttentionMetadata:
    seq_lens: list[int]
    max_seq_len: int
    batch_size: int


class FlashAttention(nn.Module):
    def __init__(self, config: FlashAttentionConfig):
        super().__init__()
        self.config = config
        self.hidden_size = config.hidden_size
        self.num_heads = config.num_heads
        self.head_dim = config.hidden_size // config.num_heads
        self.block_size = config.block_size
        self.causal = config.causal
        self.use_flash_kernel = config.use_flash_kernel
        self.scale = config.softmax_scale or (self.head_dim ** -0.5)

        self.q_proj = nn.Linear(config.hidden_size, config.hidden_size)
        self.k_proj = nn.Linear(config.hidden_size, config.hidden_size)
        self.v_proj = nn.Linear(config.hidden_size, config.hidden_size)
        self.out_proj = nn.Linear(config.hidden_size, config.hidden_size)
        self.dropout = nn.Dropout(config.dropout)

    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        B, T, C = x.shape
        q = self.q_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)

        if self.use_flash_kernel and T > self.block_size:
            out = self._blockwise_attention(q, k, v, mask)
        else:
            out = self._standard_attention(q, k, v, mask)

        out = out.transpose(1, 2).contiguous().view(B, T, C)
        return self.out_proj(out)

    def _standard_attention(self, q: torch.Tensor, k: torch.Tensor, v: torch.Tensor, mask: Optional[torch.Tensor]) -> torch.Tensor:
        with torch.backends.cuda.sdp_kernel(enable_flash=True, enable_math=True, enable_mem_efficient=True):
            return F.scaled_dot_product_attention(
                q, k, v,
                attn_mask=mask,
                dropout_p=self.dropout.p if self.training else 0.0,
                is_causal=self.causal,
            )

    def _blockwise_attention(self, q: torch.Tensor, k: torch.Tensor, v: torch.Tensor, mask: Optional[torch.Tensor]) -> torch.Tensor:
        B, H, T, D = q.shape
        block_size = self.block_size
        num_blocks = (T + block_size - 1) // block_size

        q = q.reshape(B, H, num_blocks, block_size, D)
        k = k.reshape(B, H, num_blocks, block_size, D)
        v = v.reshape(B, H, num_blocks, block_size, D)

        scale = self.scale
        out = torch.empty_like(q)

        for bi in range(B):
            for hi in range(H):
                q_block = q[bi, hi]
                k_block = k[bi, hi]
                v_block = v[bi, hi]

                m_i = torch.full((block_size,), -float("inf"), device=q.device, dtype=q.dtype)
                l_i = torch.zeros(block_size, device=q.device, dtype=q.dtype)
                o_i = torch.zeros(block_size, D, device=q.device, dtype=q.dtype)

                for j in range(num_blocks):
                    k_j = k_block[j]
                    v_j = v_block[j]
                    q_i = q_block

                    s_ij = torch.matmul(q_i, k_j.transpose(-2, -1)) * scale
                    if self.causal:
                        causal_mask = torch.triu(torch.ones(block_size, block_size, device=q.device, dtype=torch.bool), diagonal=1)
                        s_ij = s_ij.masked_fill(causal_mask, -float("inf"))

                    m_prev = m_i.clone()
                    m_i = torch.maximum(m_i, s_ij.max(dim=-1).values)
                    l_i = l_i * torch.exp(m_prev - m_i) + torch.exp(s_ij - m_i.unsqueeze(-1)).sum(dim=-1)
                    o_i = o_i * torch.exp(m_prev - m_i).unsqueeze(-1) + torch.matmul(torch.exp(s_ij - m_i.unsqueeze(-1)), v_j)

                out[bi, hi] = o_i / l_i.unsqueeze(-1)

        return out.reshape(B, H, T, D)
