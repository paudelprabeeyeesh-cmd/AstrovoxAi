"""Expert parallelism: distribute MoE experts across ranks."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


@dataclass
class ExpertParallelConfig:
    world_size: int = 1
    rank: int = 0
    num_experts: int = 1
    experts_per_rank: int = 1
    capacity_factor: float = 1.25
    top_k: int = 1


class ExpertParallelism:
    def __init__(self, config: ExpertParallelConfig):
        self.config = config
        self.world_size = config.world_size
        self.rank = config.rank
        self.num_experts = config.num_experts
        self.experts_per_rank = config.experts_per_rank
        self.capacity_factor = config.capacity_factor
        self.top_k = config.top_k
        self.local_experts: nn.ModuleList = nn.ModuleList()
        self.expert_routing_table: Dict[int, int] = {}

    def assign_experts(self, experts: nn.ModuleList) -> None:
        start = self.rank * self.experts_per_rank
        end = min(start + self.experts_per_rank, len(experts))
        self.local_experts = nn.ModuleList([experts[i] for i in range(start, end)])
        for local_idx, global_idx in enumerate(range(start, end)):
            self.expert_routing_table[global_idx] = local_idx

    def route_tokens(self, tokens: torch.Tensor,
                     gate_logits: torch.Tensor
                     ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        topk_scores, topk_indices = torch.topk(
            gate_logits, self.top_k, dim=-1
        )
        topk_scores = torch.softmax(topk_scores, dim=-1)
        flat_indices = topk_indices.view(-1)
        dispatched: Dict[int, List[torch.Tensor]] = {}
        for token_idx, expert_id in enumerate(flat_indices.tolist()):
            dispatched.setdefault(expert_id, []).append(
                tokens[token_idx // self.top_k]
            )
        return topk_scores, topk_indices, flat_indices

    def get_local_expert_output(self, expert_id: int, tokens: List[torch.Tensor]) -> torch.Tensor:
        if expert_id not in self.expert_routing_table:
            local_expert = None
            for ep in _expert_registry:
                if expert_id in ep.expert_routing_table:
                    local_expert = ep
                    break
            if local_expert is None:
                return torch.stack(tokens).sum(dim=0) if tokens else torch.tensor(0.0, device=tokens[0].device if tokens else "cpu")
            local_idx = local_expert.expert_routing_table[expert_id]
            expert = local_expert.local_experts[local_idx]
        else:
            local_idx = self.expert_routing_table[expert_id]
            expert = self.local_experts[local_idx]
        stacked = torch.stack(tokens)
        return expert(stacked.to(next(expert.parameters()).device))

    def dispatch_and_combine(self, tokens: torch.Tensor,
                              gate_logits: torch.Tensor) -> torch.Tensor:
        topk_scores, topk_indices, flat_indices = self.route_tokens(
            tokens, gate_logits
        )
        unique_experts = sorted(set(flat_indices.tolist()))
        expert_inputs: Dict[int, List[torch.Tensor]] = {}
        for token_idx, expert_id in enumerate(flat_indices.tolist()):
            expert_inputs.setdefault(expert_id, []).append(
                tokens[token_idx // self.top_k]
            )
        expert_outputs: Dict[int, torch.Tensor] = {}
        for expert_id in unique_experts:
            if expert_id in self.expert_routing_table:
                expert_outputs[expert_id] = self.get_local_expert_output(
                    expert_id, expert_inputs[expert_id]
                )
            else:
                expert_outputs[expert_id] = (
                    torch.stack(expert_inputs[expert_id]).sum(dim=0)
                    if expert_inputs[expert_id]
                    else torch.zeros_like(tokens[0])
                )
        combined = torch.zeros_like(tokens)
        for token_idx, expert_id in enumerate(flat_indices.tolist()):
            k = token_idx % self.top_k
            combined[token_idx // self.top_k] = (
                combined[token_idx // self.top_k]
                + topk_scores[token_idx // self.top_k, k]
                * expert_outputs[expert_id]
            )
        return combined

    def load_balance_loss(self, gate_logits: torch.Tensor) -> torch.Tensor:
        probs = torch.softmax(gate_logits, dim=-1)
        mean_prob = probs.mean(dim=0)
        aux_loss = self.num_experts * torch.sum(mean_prob * torch.log(mean_prob + 1e-8))
        return aux_loss


_expert_registry: List[ExpertParallelism] = []


def register_expert_parallelism(ep: ExpertParallelism) -> None:
    _expert_registry.append(ep)
