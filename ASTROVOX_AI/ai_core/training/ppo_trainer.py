from typing import Optional, Dict, Any
import torch
import torch.nn as nn
import torch.nn.functional as F


class PPOTrainer:
    def __init__(self, policy_model: nn.Module, value_model: nn.Module, reward_fn: callable, lr: float = 1e-5, gamma: float = 0.99, lam: float = 0.95, clip_eps: float = 0.2, entropy_coef: float = 0.01, value_loss_coef: float = 0.5):
        self.policy_model = policy_model
        self.value_model = value_model
        self.reward_fn = reward_fn
        self.lr = lr
        self.gamma = gamma
        self.lam = lam
        self.clip_eps = clip_eps
        self.entropy_coef = entropy_coef
        self.value_loss_coef = value_loss_coef
        self.policy_optimizer = torch.optim.AdamW(policy_model.parameters(), lr=lr)
        self.value_optimizer = torch.optim.AdamW(value_model.parameters(), lr=lr)

    def compute_advantages(self, rewards: torch.Tensor, values: torch.Tensor, dones: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        advantages = torch.zeros_like(rewards)
        last_gae = 0.0
        for t in reversed(range(len(rewards))):
            if t == len(rewards) - 1:
                next_value = 0.0
            else:
                next_value = values[t + 1]
            delta = rewards[t] + self.gamma * next_value * (1 - dones[t]) - values[t]
            advantages[t] = last_gae = delta + self.gamma * self.lam * (1 - dones[t]) * last_gae
        returns = advantages + values
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        return advantages, returns

    def update(self, states: torch.Tensor, actions: torch.Tensor, old_log_probs: torch.Tensor, advantages: torch.Tensor, returns: torch.Tensor) -> Dict[str, float]:
        logits = self.policy_model(states)
        log_probs = F.log_softmax(logits, dim=-1)
        new_log_probs = log_probs.gather(-1, actions.unsqueeze(-1)).squeeze(-1)
        ratio = (new_log_probs - old_log_probs).exp()
        surr1 = ratio * advantages
        surr2 = torch.clamp(ratio, 1 - self.clip_eps, 1 + self.clip_eps) * advantages
        policy_loss = -torch.min(surr1, surr2).mean()
        values = self.value_model(states).squeeze(-1)
        value_loss = F.mse_loss(values, returns)
        entropy = -(F.softmax(logits, dim=-1) * F.log_softmax(logits, dim=-1)).sum(-1).mean()
        total_loss = policy_loss + self.value_loss_coef * value_loss - self.entropy_coef * entropy
        self.policy_optimizer.zero_grad()
        self.value_optimizer.zero_grad()
        total_loss.backward()
        self.policy_optimizer.step()
        self.value_optimizer.step()
        return {'policy_loss': policy_loss.item(), 'value_loss': value_loss.item(), 'entropy': entropy.item(), 'total_loss': total_loss.item()}
