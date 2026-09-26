"""MoE routing service wrapper for inference workloads."""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

import torch
import torch.nn as nn

from ASTROVOX_AI.ai_core.inference.moe_inference_router import MoEInferenceRouter, MoEInferenceConfig
from ASTROVOX_AI.ai_core.foundation_moe import MoELayer, MoEConfig

logger = logging.getLogger(__name__)


class MoERoutingService:
    def __init__(self, num_experts: int = 8, top_k: int = 2, capacity_factor: float = 1.25, balance_strategy: str = "random"):
        self.config = MoEInferenceConfig(
            num_experts=num_experts,
            top_k=top_k,
            capacity_factor=capacity_factor,
            balance_strategy=balance_strategy,
        )
        self.router = MoEInferenceRouter(self.config)

    def route(self, hidden_states: torch.Tensor, gate: nn.Linear) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        return self.router.route(hidden_states, gate)

    def dispatch(self, flat_input: torch.Tensor, topk_indices: torch.Tensor, topk_probs: torch.Tensor) -> Dict[int, torch.Tensor]:
        return self.router.dispatch(flat_input, topk_indices, topk_probs)

    def get_load_stats(self) -> Dict[str, float]:
        return self.router.get_load_stats()

    def get_affinity(self, hidden_states: torch.Tensor, gate: nn.Linear) -> Dict[int, float]:
        return self.router.get_affinity(hidden_states, gate)
