"""
DPO (Direct Preference Optimization) trainer.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Optional

import torch
import torch.nn.functional as F

logger = logging.getLogger(__name__)


@dataclass
class DPOConfig:
    beta: float = 0.1
    lr: float = 1e-5
    max_grad_norm: float = 1.0


class DPOTrainer:
    def __init__(self, policy: torch.nn.Module, reference: torch.nn.Module, config: Optional[DPOConfig] = None):
        self.policy = policy
        self.reference = reference
        self.config = config or DPOConfig()
        self.optimizer = torch.optim.AdamW(self.policy.parameters(), lr=self.config.lr)

    def train_step(self, chosen_ids: torch.Tensor, rejected_ids: torch.Tensor) -> Dict[str, float]:
        chosen_logits = self.policy(chosen_ids)
        rejected_logits = self.policy(rejected_ids)
        with torch.no_grad():
            chosen_ref = self.reference(chosen_ids)
            rejected_ref = self.reference(rejected_ids)

        chosen_logps = F.log_softmax(chosen_logits, dim=-1).gather(-1, chosen_logits.argmax(dim=-1, keepdim=True)).squeeze(-1)
        rejected_logps = F.log_softmax(rejected_logits, dim=-1).gather(-1, rejected_logits.argmax(dim=-1, keepdim=True)).squeeze(-1)
        chosen_ref_logps = F.log_softmax(chosen_ref, dim=-1).gather(-1, chosen_ref.argmax(dim=-1, keepdim=True)).squeeze(-1)
        rejected_ref_logps = F.log_softmax(rejected_ref, dim=-1).gather(-1, rejected_ref.argmax(dim=-1, keepdim=True)).squeeze(-1)

        logits_diff = self.config.beta * ((chosen_logps - chosen_ref_logps) - (rejected_logps - rejected_ref_logps))
        loss = -F.logsigmoid(logits_diff).mean()
        accuracy = (logits_diff > 0).float().mean()

        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.policy.parameters(), self.config.max_grad_norm)
        self.optimizer.step()
        return {"loss": loss.item(), "dpo_accuracy": accuracy.item()}
