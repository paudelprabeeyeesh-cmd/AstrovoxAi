"""FlashAttention service wrapper for backend inference."""

from __future__ import annotations

import logging
from typing import Optional

import torch
import torch.nn as nn

from ASTROVOX_AI.ai_core.inference.flash_attention import FlashAttention, FlashAttentionConfig
from ASTROVOX_AI.ai_core.inference.triton_optimized_attention import TritonFlashAttention, TritonAttentionConfig

logger = logging.getLogger(__name__)


class FlashAttentionService:
    def __init__(self, hidden_size: int, num_heads: int, use_triton: bool = False, **kwargs):
        self.use_triton = use_triton
        if use_triton:
            config = TritonAttentionConfig(hidden_size=hidden_size, num_heads=num_heads, **kwargs)
            self.model = TritonFlashAttention(config)
        else:
            config = FlashAttentionConfig(hidden_size=hidden_size, num_heads=num_heads, **kwargs)
            self.model = FlashAttention(config)

    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        return self.model(x, mask=mask)

    def to(self, device: torch.device) -> "FlashAttentionService":
        self.model.to(device)
        return self

    def get_config(self) -> dict:
        return {
            "hidden_size": self.model.hidden_size,
            "num_heads": self.model.num_heads,
            "head_dim": self.model.head_dim,
            "use_triton": self.use_triton,
        }
