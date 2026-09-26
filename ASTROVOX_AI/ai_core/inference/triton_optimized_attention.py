"""Triton-optimized FlashAttention kernels for memory-efficient inference."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


@dataclass
class TritonAttentionConfig:
    hidden_size: int
    num_heads: int
    dropout: float = 0.0
    causal: bool = True
    block_size: int = 128
    softmax_scale: Optional[float] = None


class TritonFlashAttention(nn.Module):
    def __init__(self, config: TritonAttentionConfig):
        super().__init__()
        self.config = config
        self.hidden_size = config.hidden_size
        self.num_heads = config.num_heads
        self.head_dim = config.hidden_size // config.num_heads
        self.causal = config.causal
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

        try:
            from ASTROVOX_AI.ai_core.cuda.triton_kernels import TritonKernels
            out = TritonKernels.flash_attention(q, k, v, causal=self.causal)
            return self.out_proj(out.reshape(B, T, C))
        except ImportError:
            logger.debug("Triton kernels unavailable, falling back to SDPA")

        with torch.backends.cuda.sdp_kernel(enable_flash=True, enable_math=True, enable_mem_efficient=True):
            out = F.scaled_dot_product_attention(
                q, k, v,
                attn_mask=mask,
                dropout_p=self.dropout.p if self.training else 0.0,
                is_causal=self.causal,
            )
        out = out.transpose(1, 2).contiguous().view(B, T, C)
        return self.out_proj(out)
