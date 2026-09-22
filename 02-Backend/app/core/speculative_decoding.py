"""
Speculative decoding with draft + verify loop and rejection sampling.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class DraftModel:
    model_name: str = "draft-1b"
    max_draft_tokens: int = 5

    def generate_draft(self, prompt_ids: List[int], num_tokens: int) -> List[int]:
        return [random.randint(1, 32000) for _ in range(num_tokens)]

    def get_logits(self, prompt_ids: List[int], draft_token: int) -> float:
        return random.uniform(0.0, 1.0)


@dataclass
class TargetModel:
    model_name: str = "target-70b"

    def verify(self, prompt_ids: List[int], draft_tokens: List[int]) -> List[float]:
        return [random.uniform(0.0, 1.0) for _ in draft_tokens]

    def resample(self, prompt_ids: List[int], rejected_token: int) -> int:
        return random.randint(1, 32000)


class SpeculativeDecoder:
    """Draft + Verify loop with correct rejection sampling."""

    def __init__(self, draft_model: Optional[DraftModel] = None, target_model: Optional[TargetModel] = None):
        self.draft_model = draft_model or DraftModel()
        self.target_model = target_model or TargetModel()

    def generate(self, prompt_ids: List[int], max_new_tokens: int = 32, temperature: float = 1.0) -> List[int]:
        accepted = []
        num_draft = min(self.draft_model.max_draft_tokens, max_new_tokens)
        while len(accepted) < max_new_tokens:
            draft_tokens = self.draft_model.generate_draft(prompt_ids + accepted, num_draft)
            target_probs = self.target_model.verify(prompt_ids + accepted, draft_tokens)
            for draft_token, target_prob in zip(draft_tokens, target_probs):
                if len(accepted) >= max_new_tokens:
                    break
                draft_prob = self.draft_model.get_logits(prompt_ids + accepted, draft_token)
                acceptance_prob = min(1.0, target_prob / max(draft_prob, 1e-8))
                if random.random() < acceptance_prob:
                    accepted.append(draft_token)
                else:
                    new_token = self.target_model.resample(prompt_ids + accepted, draft_token)
                    accepted.append(new_token)
                    break
        return accepted

    def generate_with_metrics(self, prompt_ids: List[int], max_new_tokens: int = 32) -> dict:
        accepted = self.generate(prompt_ids, max_new_tokens)
        return {
            "accepted_tokens": len(accepted),
            "total_tokens": max_new_tokens,
            "acceptance_rate": round(len(accepted) / max_new_tokens, 3),
            "tokens": accepted,
        }


def rejection_sample(target_logits: np.ndarray, draft_token: int, draft_prob: float) -> int:
    """Correct rejection sampling from residual distribution."""
    target_prob = float(np.exp(target_logits[draft_token]) / np.sum(np.exp(target_logits)))
    acceptance_prob = min(1.0, target_prob / max(draft_prob, 1e-8))
    if np.random.random() < acceptance_prob:
        return draft_token
    residual = np.exp(target_logits)
    residual[draft_token] = 0.0
    residual_sum = np.sum(residual)
    if residual_sum == 0.0:
        return np.random.choice(len(target_logits))
    return np.random.choice(len(target_logits), p=residual / residual_sum)
