"""
RLHF (Reinforcement Learning from Human Feedback) trainer.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


@dataclass
class RLHFConfig:
    kl_coef: float = 0.1
    lr: float = 1e-5
    max_grad_norm: float = 1.0
    reward_scale: float = 1.0


class RLHFTrainer:
    def __init__(self, policy: nn.Module, reference: nn.Module, reward_model: nn.Module, config: Optional[RLHFConfig] = None):
        self.policy = policy
        self.reference = reference
        self.reward_model = reward_model
        self.config = config or RLHFConfig()
        self.optimizer = torch.optim.AdamW(self.policy.parameters(), lr=self.config.lr)

    def train_step(self, prompt_ids: torch.Tensor, response_ids: torch.Tensor) -> Dict[str, float]:
        full_ids = torch.cat([prompt_ids, response_ids], dim=1)
        logits = self.policy(full_ids)
        log_probs = F.log_softmax(logits, dim=-1)
        response_log_probs = log_probs[:, prompt_ids.shape[1] - 1 : -1, :].gather(2, response_ids.unsqueeze(-1)).squeeze(-1).sum(-1)

        with torch.no_grad():
            ref_logits = self.reference(full_ids)
            ref_log_probs = F.log_softmax(ref_logits, dim=-1)
            ref_response_log_probs = ref_log_probs[:, prompt_ids.shape[1] - 1 : -1, :].gather(2, response_ids.unsqueeze(-1)).squeeze(-1).sum(-1)

        rewards = self.reward_model(full_ids).detach()
        kl_penalty = self.config.kl_coef * (response_log_probs - ref_response_log_probs).mean()
        loss = -(rewards.mean() - kl_penalty)

        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.policy.parameters(), self.config.max_grad_norm)
        self.optimizer.step()
        return {"loss": loss.item(), "kl_penalty": kl_penalty.item(), "reward": rewards.mean().item()}
