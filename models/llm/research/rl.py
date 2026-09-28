from __future__ import annotations

from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F

# ---------------------------------------------------------------------------
# 1. Policy and Value Networks
# ---------------------------------------------------------------------------


class PolicyNetwork(nn.Module):
    """Actor network for PPO policy gradient."""

    def __init__(
        self,
        input_size: int = 768,
        hidden_size: int = 1024,
        output_size: int = 32000,
        num_layers: int = 4,
        device=None,
        dtype=None,
    ):
        super().__init__()
        layers = []
        for i in range(num_layers):
            in_dim = input_size if i == 0 else hidden_size
            layers.append(nn.Linear(in_dim, hidden_size, device=device, dtype=dtype))
            layers.append(nn.ReLU())
        layers.append(nn.Linear(hidden_size, output_size, device=device, dtype=dtype))
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class ValueNetwork(nn.Module):
    """Critic network estimating state value."""

    def __init__(
        self,
        input_size: int = 768,
        hidden_size: int = 1024,
        num_layers: int = 4,
        device=None,
        dtype=None,
    ):
        super().__init__()
        layers = []
        for i in range(num_layers):
            in_dim = input_size if i == 0 else hidden_size
            layers.append(nn.Linear(in_dim, hidden_size, device=device, dtype=dtype))
            layers.append(nn.ReLU())
        layers.append(nn.Linear(hidden_size, 1, device=device, dtype=dtype))
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


# ---------------------------------------------------------------------------
# 2. Reward Model
# ---------------------------------------------------------------------------


class RewardModel(nn.Module):
    """Reward model predicting scalar rewards for LLM outputs."""

    def __init__(
        self,
        vocab_size: int = 32000,
        hidden_size: int = 768,
        num_layers: int = 4,
        num_attention_heads: int = 12,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, hidden_size, device=device, dtype=dtype)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_size, nhead=num_attention_heads, batch_first=True,
            device=device, dtype=dtype,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.ln = nn.LayerNorm(hidden_size, device=device, dtype=dtype)
        self.head = nn.Linear(hidden_size, 1, device=device, dtype=dtype)

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        x = self.embedding(input_ids)
        src_key_padding_mask = (attention_mask == 0) if attention_mask is not None else None
        x = self.encoder(x, src_key_padding_mask=src_key_padding_mask)
        x = self.ln(x)
        if attention_mask is not None:
            lengths = attention_mask.sum(dim=1, keepdim=True)
            x = (x * attention_mask.unsqueeze(-1)).sum(dim=1) / lengths.clamp(min=1)
        else:
            x = x.mean(dim=1)
        return self.head(x).squeeze(-1)


# ---------------------------------------------------------------------------
# 3. Environment Interface
# ---------------------------------------------------------------------------


@dataclass
class EnvironmentStep:
    observation: torch.Tensor
    reward: float
    done: bool
    info: dict


class LLMEnvironment:
    """Environment interface for LLM reinforcement learning."""

    def __init__(
        self,
        tokenizer: object,
        reward_fn: callable,
        max_steps: int = 256,
        device: torch.device | None = None,
    ):
        self.tokenizer = tokenizer
        self.reward_fn = reward_fn
        self.max_steps = max_steps
        self.device = device or torch.device("cpu")
        self.current_step = 0

    def reset(self, prompt: str) -> torch.Tensor:
        self.current_step = 0
        if hasattr(self.tokenizer, "encode"):
            obs = torch.tensor(
                self.tokenizer.encode(prompt), device=self.device, dtype=torch.long
            ).unsqueeze(0)
        else:
            obs = torch.zeros(1, 1, device=self.device, dtype=torch.long)
        return obs

    def step(self, action: torch.Tensor) -> EnvironmentStep:
        self.current_step += 1
        if hasattr(self.tokenizer, "decode"):
            text = self.tokenizer.decode(action.tolist())
        else:
            text = ""
        reward = float(self.reward_fn(text))
        done = self.current_step >= self.max_steps
        obs = action
        return EnvironmentStep(observation=obs, reward=reward, done=done, info={"text": text})


# ---------------------------------------------------------------------------
# 4. PPO Trainer
# ---------------------------------------------------------------------------


class PPOTrainer:
    """Proximal Policy Optimization trainer for language models."""

    def __init__(
        self,
        policy: PolicyNetwork,
        value_net: ValueNetwork,
        reward_model: RewardModel,
        clip_eps: float = 0.2,
        entropy_coef: float = 0.01,
        value_loss_coef: float = 0.5,
        max_grad_norm: float = 1.0,
        device: torch.device | None = None,
    ):
        self.policy = policy
        self.value_net = value_net
        self.reward_model = reward_model
        self.clip_eps = clip_eps
        self.entropy_coef = entropy_coef
        self.value_loss_coef = value_loss_coef
        self.max_grad_norm = max_grad_norm
        self.device = device or next(policy.parameters()).device
        self.optimizer = torch.optim.AdamW(
            list(self.policy.parameters()) + list(self.value_net.parameters()), lr=1e-5
        )

    def compute_advantages(
        self,
        rewards: torch.Tensor,
        values: torch.Tensor,
        gamma: float = 0.99,
        lam: float = 0.95,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        deltas = rewards - values
        advantages = torch.zeros_like(rewards)
        last_adv = 0.0
        for t in reversed(range(len(rewards))):
            last_adv = deltas[t] + gamma * lam * last_adv
            advantages[t] = last_adv
        returns = advantages + values
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        return advantages, returns

    def train_step(
        self,
        observations: torch.Tensor,
        actions: torch.Tensor,
        old_log_probs: torch.Tensor,
        rewards: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
    ) -> dict[str, float]:
        with torch.no_grad():
            values = self.value_net(observations)
            advantages, returns = self.compute_advantages(rewards, values)
        logits = self.policy(observations)
        logits = logits.gather(-1, actions.unsqueeze(-1)).squeeze(-1)
        log_probs = F.log_softmax(logits, dim=-1)
        ratio = (log_probs - old_log_probs).exp()
        clipped_ratio = torch.clamp(ratio, 1.0 - self.clip_eps, 1.0 + self.clip_eps)
        policy_loss = -torch.min(ratio * advantages, clipped_ratio * advantages).mean()
        value_loss = F.mse_loss(self.value_net(observations), returns)
        entropy = -(log_probs.exp() * log_probs).sum(-1).mean()
        total_loss = policy_loss + self.value_loss_coef * value_loss - self.entropy_coef * entropy
        self.optimizer.zero_grad()
        total_loss.backward()
        nn.utils.clip_grad_norm_(self.policy.parameters(), self.max_grad_norm)
        nn.utils.clip_grad_norm_(self.value_net.parameters(), self.max_grad_norm)
        self.optimizer.step()
        return {
            "policy_loss": policy_loss.item(),
            "value_loss": value_loss.item(),
            "entropy": entropy.item(),
            "total_loss": total_loss.item(),
        }
