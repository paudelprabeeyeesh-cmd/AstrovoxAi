from typing import Optional, Dict, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F


class RLHFConfig:
    def __init__(self, reward_model_path: Optional[str] = None, kl_coef: float = 0.1, lr: float = 1e-5, num_train_epochs: int = 3, max_length: int = 512):
        self.reward_model_path = reward_model_path
        self.kl_coef = kl_coef
        self.lr = lr
        self.num_train_epochs = num_train_epochs
        self.max_length = max_length


class RLHFTrainer:
    def __init__(self, policy_model: nn.Module, reward_model: nn.Module, reference_model: nn.Module, config: RLHFConfig):
        self.policy_model = policy_model
        self.reward_model = reward_model
        self.reference_model = reference_model
        self.config = config
        self.kl_coef = config.kl_coef

    def compute_rewards(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            rewards = self.reward_model(input_ids, attention_mask)
        return rewards

    def policy_gradient_step(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        logits = self.policy_model(input_ids, attention_mask)
        rewards = self.compute_rewards(input_ids, attention_mask)
        with torch.no_grad():
            ref_logits = self.reference_model(input_ids, attention_mask)
        kl_div = F.kl_div(F.log_softmax(logits, dim=-1), F.softmax(ref_logits, dim=-1), reduction='batchmean')
        advantages = rewards - self.kl_coef * kl_div
        loss = -advantages.mean()
        return loss, kl_div

    def train_step(self, batch: Dict[str, torch.Tensor]) -> Dict[str, float]:
        input_ids = batch['input_ids']
        attention_mask = batch['attention_mask']
        loss, kl_div = self.policy_gradient_step(input_ids, attention_mask)
        loss.backward()
        return {'loss': loss.item(), 'kl_div': kl_div.item()}
