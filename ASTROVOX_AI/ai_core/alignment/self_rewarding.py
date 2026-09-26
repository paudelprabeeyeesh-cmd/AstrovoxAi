from typing import Optional, Dict, Any, List
import torch
import torch.nn as nn
import logging

logger = logging.getLogger(__name__)


class SelfRewardingTrainer:
    def __init__(self, model: nn.Module, reward_head: nn.Module, lr: float = 1e-6):
        self.model = model
        self.reward_head = reward_head
        self.lr = lr
        self.optimizer = torch.optim.AdamW(list(model.parameters()) + list(reward_head.parameters()), lr=lr)

    def train_step(self, prompts: List[str], responses: List[str]) -> Tuple[float, float]:
        inputs = self.model.tokenizer(prompts, responses, padding=True, truncation=True, return_tensors='pt')
        outputs = self.model(**inputs, output_hidden_states=True)
        hidden_states = outputs.hidden_states[-1]
        rewards = self.reward_head(hidden_states.mean(dim=1))
        loss = -rewards.mean()
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        return loss.item(), rewards.mean().item()
