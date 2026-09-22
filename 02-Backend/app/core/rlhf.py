"""
RLHF/PPO training loop and Constitutional AI self-critique pipeline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


@dataclass
class PPOConfig:
    clip_eps: float = 0.2
    value_loss_coef: float = 0.5
    entropy_coef: float = 0.01
    kl_coef: float = 0.1
    max_grad_norm: float = 1.0


class RewardModel(nn.Module):
    """Simple reward model: transformer with scalar head."""

    def __init__(self, base_model: nn.Module):
        super().__init__()
        self.base_model = base_model
        with torch.no_grad():
            dummy = torch.randint(0, 100, (1, 4))
            hidden = base_model(dummy)
            hidden_size = hidden.shape[-1]
        self.reward_head = nn.Linear(hidden_size, 1)

    def forward(self, input_ids: torch.Tensor, attention_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        with torch.no_grad():
            hidden = self.base_model(input_ids, attention_mask=attention_mask)
        last_token_hidden = hidden[:, -1, :]
        return self.reward_head(last_token_hidden).squeeze(-1)


def compute_advantages(rewards: torch.Tensor, values: torch.Tensor, gamma: float = 0.99, lam: float = 0.95) -> Tuple[torch.Tensor, torch.Tensor]:
    """Generalized Advantage Estimation (GAE)."""
    advantages = torch.zeros_like(rewards)
    gae = 0.0
    for t in reversed(range(len(rewards))):
        if t == len(rewards) - 1:
            next_value = 0.0
        else:
            next_value = values[t + 1]
        delta = rewards[t] + gamma * next_value - values[t]
        gae = delta + gamma * lam * gae
        advantages[t] = gae
    returns = advantages + values
    return advantages, returns


def ppo_loss(
    old_log_probs: torch.Tensor,
    new_log_probs: torch.Tensor,
    advantages: torch.Tensor,
    config: PPOConfig,
) -> torch.Tensor:
    """Clipped PPO surrogate objective with KL penalty."""
    ratio = (new_log_probs - old_log_probs).exp()
    clipped_ratio = torch.clamp(ratio, 1.0 - config.clip_eps, 1.0 + config.clip_eps)
    policy_loss = -torch.min(ratio * advantages, clipped_ratio * advantages).mean()
    kl_penalty = config.kl_coef * (new_log_probs - old_log_probs).mean()
    return policy_loss + kl_penalty


class RLHFTrainer:
    """PPO-based RLHF trainer."""

    def __init__(self, model: nn.Module, ref_model: nn.Module, reward_model: RewardModel, config: PPOConfig):
        self.model = model
        self.ref_model = ref_model
        self.reward_model = reward_model
        self.config = config
        self.optimizer = torch.optim.AdamW(model.parameters(), lr=1e-5)

    def train_step(self, prompt_ids: torch.Tensor, response_ids: torch.Tensor) -> float:
        full_ids = torch.cat([prompt_ids, response_ids], dim=1)
        logits = self.model(full_ids)
        log_probs = F.log_softmax(logits, dim=-1)
        response_log_probs = log_probs[:, prompt_ids.shape[1] - 1 : -1, :].gather(2, response_ids.unsqueeze(-1)).squeeze(-1).sum(-1)
        with torch.no_grad():
            ref_logits = self.ref_model(full_ids)
            ref_log_probs = F.log_softmax(ref_logits, dim=-1)
            ref_response_log_probs = ref_log_probs[:, prompt_ids.shape[1] - 1 : -1, :].gather(2, response_ids.unsqueeze(-1)).squeeze(-1).sum(-1)
        rewards = self.reward_model(full_ids).detach()
        values = torch.zeros_like(rewards)
        advantages, returns = compute_advantages(rewards, values)
        loss = ppo_loss(ref_response_log_probs, response_log_probs, advantages, self.config)
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.config.max_grad_norm)
        self.optimizer.step()
        return loss.item()


class ConstitutionalAI:
    """Self-critique pipeline: generate -> critique -> revise."""

    def __init__(self, model: nn.Module, tokenizer, principles: List[str]):
        self.model = model
        self.tokenizer = tokenizer
        self.principles = principles

    def critique(self, prompt: str, response: str) -> str:
        critique_prompt = f"Principle: {self.principles[0]}\n\nResponse: {response}\n\nCritique: Does this response violate the principle? If so, explain how."
        return self._generate(critique_prompt)

    def revise(self, prompt: str, response: str, critique: str) -> str:
        revision_prompt = f"Original prompt: {prompt}\nOriginal response: {response}\nCritique: {critique}\n\nRevised response:"
        return self._generate(revision_prompt)

    def _generate(self, prompt: str) -> str:
        if hasattr(self.tokenizer, "encode"):
            ids = self.tokenizer.encode(prompt)
            input_tensor = torch.tensor([ids])
            with torch.no_grad():
                logits = self.model(input_tensor)
            return "[generated]"
        return "[generated]"

    def run_pipeline(self, prompt: str, initial_response: str) -> Tuple[str, str, str]:
        critique = self.critique(prompt, initial_response)
        revised = self.revise(prompt, initial_response, critique)
        return initial_response, critique, revised
