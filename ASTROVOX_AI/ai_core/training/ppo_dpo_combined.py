from typing import Optional, Dict, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F


class CombinedPPODPOTrainer:
    def __init__(self, policy_model: nn.Module, reference_model: nn.Module, reward_model: nn.Module, beta: float = 0.1, lr: float = 1e-5, clip_eps: float = 0.2, kl_coef: float = 0.1, value_loss_coef: float = 0.5, entropy_coef: float = 0.01):
        self.policy_model = policy_model
        self.reference_model = reference_model
        self.reward_model = reward_model
        self.beta = beta
        self.clip_eps = clip_eps
        self.kl_coef = kl_coef
        self.value_loss_coef = value_loss_coef
        self.entropy_coef = entropy_coef
        self.policy_optimizer = torch.optim.AdamW(policy_model.parameters(), lr=lr)

    def dpo_loss(self, chosen_logits: torch.Tensor, rejected_logits: torch.Tensor, chosen_ref_logits: torch.Tensor, rejected_ref_logits: torch.Tensor) -> Tuple[torch.Tensor, Dict[str, float]]:
        chosen_logps = F.log_softmax(chosen_logits, dim=-1).gather(-1, chosen_logits.argmax(dim=-1, keepdim=True)).squeeze(-1)
        rejected_logps = F.log_softmax(rejected_logits, dim=-1).gather(-1, rejected_logits.argmax(dim=-1, keepdim=True)).squeeze(-1)
        chosen_ref_logps = F.log_softmax(chosen_ref_logits, dim=-1).gather(-1, chosen_ref_logits.argmax(dim=-1, keepdim=True)).squeeze(-1)
        rejected_ref_logps = F.log_softmax(rejected_ref_logits, dim=-1).gather(-1, rejected_ref_logits.argmax(dim=-1, keepdim=True)).squeeze(-1)
        logits_diff = self.beta * ((chosen_logps - chosen_ref_logps) - (rejected_logps - rejected_ref_logps))
        dpo_loss = -F.logsigmoid(logits_diff).mean()
        accuracy = (logits_diff > 0).float().mean()
        return dpo_loss, {'dpo_accuracy': accuracy.item()}

    def ppo_loss(self, old_log_probs: torch.Tensor, new_log_probs: torch.Tensor, advantages: torch.Tensor) -> Tuple[torch.Tensor, Dict[str, float]]:
        ratio = (new_log_probs - old_log_probs).exp()
        clipped_ratio = torch.clamp(ratio, 1.0 - self.clip_eps, 1.0 + self.clip_eps)
        policy_loss = -torch.min(ratio * advantages, clipped_ratio * advantages).mean()
        kl_penalty = self.kl_coef * (new_log_probs - old_log_probs).mean()
        entropy = -(F.softmax(new_log_probs, dim=-1) * F.log_softmax(new_log_probs, dim=-1)).sum(-1).mean()
        total_loss = policy_loss + kl_penalty - self.entropy_coef * entropy
        return total_loss, {'policy_loss': policy_loss.item(), 'kl_penalty': kl_penalty.item(), 'entropy': entropy.item()}

    def combined_train_step(self, prompt_ids: torch.Tensor, chosen_ids: torch.Tensor, rejected_ids: torch.Tensor, old_log_probs: Optional[torch.Tensor] = None) -> Dict[str, float]:
        chosen_logits = self.policy_model(chosen_ids)
        rejected_logits = self.policy_model(rejected_ids)
        with torch.no_grad():
            chosen_ref_logits = self.reference_model(chosen_ids)
            rejected_ref_logits = self.reference_model(rejected_ids)
        dpo_loss, dpo_metrics = self.dpo_loss(chosen_logits, rejected_logits, chosen_ref_logits, rejected_ref_logits)
        full_chosen = torch.cat([prompt_ids, chosen_ids], dim=1)
        rewards = self.reward_model(full_chosen).detach()
        response_logits = self.policy_model(full_chosen)
        response_log_probs = F.log_softmax(response_logits, dim=-1).gather(-1, chosen_ids.unsqueeze(-1)).squeeze(-1).sum(-1)
        if old_log_probs is not None:
            advantages = rewards - old_log_probs
            ppo_loss, ppo_metrics = self.ppo_loss(old_log_probs, response_log_probs, advantages)
        else:
            ppo_loss = rewards.mean()
            ppo_metrics = {}
        total_loss = dpo_loss + ppo_loss
        self.policy_optimizer.zero_grad()
        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.policy_model.parameters(), 1.0)
        self.policy_optimizer.step()
        return {**dpo_metrics, **ppo_metrics, 'total_loss': total_loss.item(), 'dpo_loss': dpo_loss.item(), 'ppo_loss': ppo_loss.item()}
