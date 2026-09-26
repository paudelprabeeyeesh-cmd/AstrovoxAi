"""Speculative decoding service wrapper for inference."""

from __future__ import annotations

import logging
from typing import Optional, Tuple

import torch
import torch.nn as nn

from ASTROVOX_AI.ai_core.inference.speculative_decoding import SpeculativeDecoder
from ASTROVOX_AI.ai_core.inference.speculative_decoding_v2 import EnhancedSpeculativeDecoder

logger = logging.getLogger(__name__)


class SpeculativeDecodingService:
    def __init__(self, target_model: nn.Module, draft_model: nn.Module, gamma: int = 4, use_enhanced: bool = True):
        self.gamma = gamma
        if use_enhanced:
            self.decoder = EnhancedSpeculativeDecoder(target_model, draft_model, gamma)
        else:
            self.decoder = SpeculativeDecoder(target_model, draft_model, gamma)

    def decode(self, input_ids: torch.Tensor, max_new_tokens: int = 100, temperature: float = 1.0) -> Tuple[torch.Tensor, int]:
        return self.decoder.decode(input_ids, max_new_tokens)

    def generate(self, input_ids: torch.Tensor, max_new_tokens: int = 100, temperature: float = 1.0) -> torch.Tensor:
        generated, _ = self.decoder.decode(input_ids, max_new_tokens)
        return generated
