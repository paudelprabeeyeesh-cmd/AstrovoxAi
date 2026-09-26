"""MoE inference router with load balancing and expert affinity."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


@dataclass
class MoEInferenceConfig:
    num_experts: int = 8
    top_k: int = 2
    capacity_factor: float = 1.25
    balance_strategy: str = "random"
    drop_invalid: bool = True


class MoEInferenceRouter:
    def __init__(self, config: MoEInferenceConfig):
        self.config = config
        self.expert_load: Dict[int, int] = {i: 0 for i in range(config.num_experts)}
        self.expert_capacity = max(1, int(config.num_experts * config.capacity_factor))

    def route(self, hidden_states: torch.Tensor, gate: nn.Linear) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        B, T, C = hidden_states.shape
        flat = hidden_states.view(-1, C)
        gate_logits = gate(flat)
        gate_probs = F.softmax(gate_logits, dim=-1)
        topk_probs, topk_indices = torch.topk(gate_probs, self.config.top_k, dim=-1)
        topk_probs = topk_probs / topk_probs.sum(dim=-1, keepdim=True)
        expert_mask = torch.zeros_like(gate_logits).scatter_(1, topk_indices, 1)
        if self.config.balance_strategy == "random":
            self._update_random_load(topk_indices)
        elif self.config.balance_strategy == "round_robin":
            self._update_rr_load(topk_indices)
        return topk_probs, topk_indices, expert_mask

    def _update_random_load(self, topk_indices: torch.Tensor) -> None:
        flat = topk_indices.view(-1)
        for idx in flat.tolist():
            self.expert_load[idx] += 1

    def _update_rr_load(self, topk_indices: torch.Tensor) -> None:
        flat = topk_indices.view(-1)
        for idx in flat.tolist():
            min_expert = min(self.expert_load, key=self.expert_load.get)
            self.expert_load[min_expert] += 1

    def get_affinity(self, hidden_states: torch.Tensor, gate: nn.Linear) -> Dict[int, float]:
        with torch.no_grad():
            logits = gate(hidden_states.view(-1, hidden_states.shape[-1]))
            probs = F.softmax(logits, dim=-1).mean(dim=0)
        return {i: float(p.item()) for i, p in enumerate(probs)}

    def dispatch(self, flat_input: torch.Tensor, topk_indices: torch.Tensor, topk_probs: torch.Tensor) -> Dict[int, torch.Tensor]:
        dispatched: Dict[int, torch.Tensor] = {}
        for token_idx, expert_id in enumerate(topk_indices.tolist()):
            for k_idx, expert_id_k in enumerate(expert_id):
                dispatched.setdefault(expert_id_k, []).append(
                    (token_idx, flat_input[token_idx] * topk_probs[token_idx, k_idx])
                )
        return {k: torch.stack([v for _, v in vals]) for k, vals in dispatched.items()}

    def get_load_stats(self) -> Dict[str, float]:
        total = sum(self.expert_load.values()) or 1
        return {f"expert_{i}": count / total for i, count in self.expert_load.items()}
