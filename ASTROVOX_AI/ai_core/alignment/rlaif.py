from typing import Optional, Dict, Any, List, Tuple
import torch
import torch.nn as nn
import logging

logger = logging.getLogger(__name__)


class RLAIFTrainer:
    def __init__(self, model: nn.Module, reward_model: nn.Module, lr: float = 1e-6):
        self.model = model
        self.reward_model = reward_model.eval()
        self.lr = lr
        self.optimizer = torch.optim.AdamW(model.parameters(), lr=lr)

    def compute_rewards(self, prompts: List[str], responses: List[str]) -> torch.Tensor:
        with torch.no_grad():
            inputs = self.reward_model.tokenizer(prompts, responses, padding=True, truncation=True, return_tensors='pt')
            rewards = self.reward_model(**inputs).logits
        return rewards.squeeze(-1)

    def train_step(self, prompts: List[str], responses: List[str], ref_responses: List[str]) -> float:
        rewards = self.compute_rewards(prompts, responses)
        ref_rewards = self.compute_rewards(prompts, ref_responses)
        advantages = rewards - ref_rewards
        encodings = self.model.tokenizer(prompts, responses, padding=True, truncation=True, return_tensors='pt')
        outputs = self.model(**encodings, labels=encodings['input_ids'])
        loss = -outputs.logits.mean() * advantages.mean()
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        return loss.item()
