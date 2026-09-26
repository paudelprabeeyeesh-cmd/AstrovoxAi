"""Speculative decoding runner with draft model hooks and acceptance checking."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


@dataclass
class SpeculativeStats:
    draft_tokens: int = 0
    accepted_tokens: int = 0
    rejected_tokens: int = 0
    target_calls: int = 0
    draft_calls: int = 0
    acceptance_rate: float = 0.0

    def update(self, accepted: int, draft: int) -> None:
        self.accepted_tokens += accepted
        self.rejected_tokens += draft - accepted
        self.draft_tokens += draft
        self.acceptance_rate = self.accepted_tokens / max(self.draft_tokens, 1)


class SpeculativeDecoder(nn.Module):
    def __init__(
        self,
        target_model: nn.Module,
        draft_model: nn.Module,
        gamma: int = 4,
        top_p: float = 0.9,
        top_k: Optional[int] = None,
        temperature: float = 1.0,
    ):
        super().__init__()
        self.target_model = target_model
        self.draft_model = draft_model
        self.gamma = gamma
        self.top_p = top_p
        self.top_k = top_k
        self.temperature = temperature
        self.stats = SpeculativeStats()

    @torch.no_grad()
    def decode(
        self,
        input_ids: torch.Tensor,
        max_new_tokens: int = 100,
        stop_token_ids: Optional[list[int]] = None,
    ) -> tuple[torch.Tensor, SpeculativeStats]:
        device = input_ids.device
        generated = input_ids.clone()
        stop_token_ids = stop_token_ids or []
        while generated.shape[1] < input_ids.shape[1] + max_new_tokens:
            draft_tokens, draft_logits = self._draft_rollout(generated)
            target_logits = self._target_forward(generated, draft_tokens)
            accepted_indices = self._acceptance_check(draft_logits, target_logits)
            accepted_count = self._accept_slice(generated, draft_tokens, accepted_indices)
            next_token = self._sample_token(target_logits[:, -1, :])
            generated = torch.cat([generated, next_token], dim=1)
            if next_token.item() in stop_token_ids:
                break
            self.stats.update(accepted=accepted_count, draft=len(draft_tokens))
        return generated[:, : input_ids.shape[1] + max_new_tokens], self.stats

    def _draft_rollout(self, generated: torch.Tensor) -> tuple[list[torch.Tensor], list[torch.Tensor]]:
        draft_tokens: list[torch.Tensor] = []
        draft_logits: list[torch.Tensor] = []
        cur = generated
        for _ in range(self.gamma):
            logits = self.draft_model(cur)
            last_logits = logits[:, -1, :] / self.temperature
            if self.top_k is not None:
                v, _ = torch.topk(last_logits, self.top_k)
                last_logits[last_logits < v[:, [-1]]] = float("-inf")
            if self.top_p < 1.0:
                last_logits = self._top_p_filter(last_logits, self.top_p)
            probs = F.softmax(last_logits, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1)
            draft_tokens.append(next_token)
            draft_logits.append(last_logits)
            cur = torch.cat([cur, next_token], dim=1)
            self.stats.draft_calls += 1
        return draft_tokens, draft_logits

    def _target_forward(self, prefix: torch.Tensor, draft_tokens: list[torch.Tensor]) -> torch.Tensor:
        all_tokens = torch.cat([prefix] + draft_tokens, dim=1)
        logits = self.target_model(all_tokens)
        self.stats.target_calls += 1
        return logits

    def _acceptance_check(self, draft_logits: list[torch.Tensor], target_logits: torch.Tensor) -> torch.Tensor:
        draft_probs = torch.stack([F.softmax(lg, dim=-1) for lg in draft_logits], dim=1)
        target_at_draft = target_logits[:, prefix.shape[1]:-1, :]
        target_probs = F.softmax(target_at_draft, dim=-1)
        draft_token_ids = torch.cat(draft_tokens, dim=1)
        draft_token_probs = torch.gather(draft_probs, -1, draft_token_ids.unsqueeze(-1)).squeeze(-1)
        target_token_probs = torch.gather(target_probs, -1, draft_token_ids.unsqueeze(-1)).squeeze(-1)
        ratio = target_token_probs / (draft_token_probs + 1e-8)
        uniform = torch.rand_like(ratio)
        return uniform.clamp(max=1.0) <= ratio

    def _accept_slice(self, generated: torch.Tensor, draft_tokens: list[torch.Tensor], mask: torch.Tensor) -> int:
        draft_tensor = torch.cat(draft_tokens, dim=1)
        batch_size = generated.shape[0]
        accepted_counts = torch.zeros(batch_size, dtype=torch.long, device=generated.device)
        for i in range(batch_size):
            row_mask = mask[i]
            accepted = torch.argmax(row_mask.long())
            accepted_counts[i] = accepted.item() + 1
            generated = torch.cat([generated, draft_tensor[i:i+1, : accepted + 1]], dim=1)
        return accepted_counts.sum().item()

    def _sample_token(self, logits: torch.Tensor) -> torch.Tensor:
        if self.top_p < 1.0:
            logits = self._top_p_filter(logits, self.top_p)
        if self.top_k is not None:
            v, _ = torch.topk(logits, self.top_k)
            logits[logits < v[:, [-1]]] = float("-inf")
        probs = F.softmax(logits / self.temperature, dim=-1)
        return torch.multinomial(probs, num_samples=1)

    @staticmethod
    def _top_p_filter(logits: torch.Tensor, top_p: float) -> torch.Tensor:
        sorted_logits, sorted_indices = torch.sort(logits, descending=True)
        cumulative_probs = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)
        sorted_indices_to_remove = cumulative_probs > top_p
        sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
        sorted_indices_to_remove[..., 0] = False
        indices_to_remove = sorted_indices_to_remove.scatter(1, sorted_indices, sorted_indices_to_remove)
        logits[indices_to_remove] = float("-inf")
        return logits


class DraftModelHook:
    def __init__(self, draft_model: nn.Module, gamma: int = 4):
        self.draft_model = draft_model
        self.gamma = gamma

    def generate_draft(self, input_ids: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        tokens: list[torch.Tensor] = []
        logits_list: list[torch.Tensor] = []
        cur = input_ids
        for _ in range(self.gamma):
            logits = self.draft_model(cur)
            next_token = torch.argmax(logits[:, -1, :], dim=-1, keepdim=True)
            tokens.append(next_token)
            logits_list.append(logits[:, -1, :])
            cur = torch.cat([cur, next_token], dim=1)
        return torch.cat(tokens, dim=1), torch.stack(logits_list, dim=1)
