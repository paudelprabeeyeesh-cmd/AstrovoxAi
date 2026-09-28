"""Omega-9: Alignment research with RLHF, constitutional AI, and safety methods."""

import logging
from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


@dataclass
class AlignmentConfig:
    learning_rate: float = 1e-5
    kl_coef: float = 0.1
    gamma: float = 0.99
    reward_scale: float = 1.0
    max_grad_norm: float = 1.0
    safety_threshold: float = 0.8
    use_constitutional_ai: bool = False
    use_rlhf: bool = True
    use_dpo: bool = False
    use_ppo: bool = False
    use_safety_classifier: bool = True


class RewardModel(nn.Module):
    def __init__(self, hidden_size: int = 768):
        super().__init__()
        self.hidden_size = hidden_size
        self.mlp = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Linear(hidden_size // 2, 1),
        )

    def forward(self, hidden_states: torch.Tensor) -> torch.Tensor:
        return self.mlp(hidden_states.mean(dim=1)).squeeze(-1)


class PPOOptimizer:
    def __init__(self, config: AlignmentConfig):
        self.config = config
        self.clip_epsilon = 0.2

    def compute_loss(self, log_probs: torch.Tensor, old_log_probs: torch.Tensor, advantages: torch.Tensor) -> torch.Tensor:
        ratio = torch.exp(log_probs - old_log_probs.detach())
        clipped = torch.clamp(ratio, 1 - self.clip_epsilon, 1 + self.clip_epsilon)
        return -torch.min(ratio * advantages, clipped * advantages).mean()


class DPOOptimizer:
    def __init__(self, config: AlignmentConfig):
        self.config = config
        self.beta = 1.0

    def compute_loss(self, chosen_logps: torch.Tensor, rejected_logps: torch.Tensor) -> torch.Tensor:
        return -F.logsigmoid(self.beta * (chosen_logps - rejected_logps)).mean()


class ConstitutionalAI:
    def __init__(self, principles: list[str], config: AlignmentConfig):
        self.principles = principles
        self.config = config

    def critique(self, text: str) -> str:
        return f"Critique: {text}"

    def revise(self, text: str, critique: str) -> str:
        return f"Revised: {text} based on {critique}"


class SafetyClassifier:
    def __init__(self, hidden_size: int = 768, num_classes: int = 2):
        super().__init__()
        self.hidden_size = hidden_size
        self.classifier = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Linear(hidden_size // 2, num_classes),
        )

    def forward(self, hidden_states: torch.Tensor) -> torch.Tensor:
        return self.classifier(hidden_states.mean(dim=1))

    def is_safe(self, hidden_states: torch.Tensor, threshold: float = 0.8) -> torch.Tensor:
        logits = self.forward(hidden_states)
        probs = F.softmax(logits, dim=-1)
        return probs[:, 1] < threshold


class AlignmentTrainer:
    def __init__(self, model: nn.Module, config: AlignmentConfig):
        self.model = model
        self.config = config
        self.reward_model = RewardModel()
        self.ppo_optimizer = PPOOptimizer(config)
        self.dpo_optimizer = DPOOptimizer(config)
        self.constitutional_ai = ConstitutionalAI(["Be helpful", "Be harmless", "Be honest"], config)
        self.safety_classifier = SafetyClassifier()

    def rlhf_step(self, prompt: torch.Tensor, response: torch.Tensor) -> dict[str, float]:
        reward = self.reward_model(response).mean()
        return {"reward": reward.item()}

    def dpo_step(self, chosen: torch.Tensor, rejected: torch.Tensor) -> dict[str, float]:
        chosen_logps = torch.log_softmax(chosen, dim=-1).sum(dim=-1)
        rejected_logps = torch.log_softmax(rejected, dim=-1).sum(dim=-1)
        loss = self.dpo_optimizer.compute_loss(chosen_logps, rejected_logps)
        return {"loss": loss.item()}

    def safety_filter(self, hidden_states: torch.Tensor) -> torch.Tensor:
        return self.safety_classifier.is_safe(hidden_states, self.config.safety_threshold)


class AlignmentResearch:
    def __init__(self, config: AlignmentConfig | None = None):
        self.config = config or AlignmentConfig()

    def create_trainer(self, model: nn.Module) -> AlignmentTrainer:
        return AlignmentTrainer(model, self.config)
