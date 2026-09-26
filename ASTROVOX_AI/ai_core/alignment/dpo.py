from typing import Optional, Dict, Any, List, Tuple
import torch
import torch.nn as nn
import logging

logger = logging.getLogger(__name__)


class DPOTrainer:
    def __init__(self, model: nn.Module, ref_model: nn.Module, beta: float = 0.1, lr: float = 1e-6):
        self.model = model
        self.ref_model = ref_model.eval()
        self.beta = beta
        self.lr = lr
        self.optimizer = torch.optim.AdamW(model.parameters(), lr=lr)

    def _compute_logits(self, model: nn.Module, input_ids: torch.Tensor, attention_mask: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
        return outputs.logits

    def _compute_rewards(self, chosen_logits: torch.Tensor, rejected_logits: torch.Tensor, chosen_labels: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        chosen_loss = nn.functional.cross_entropy(chosen_logits.view(-1, chosen_logits.size(-1)), chosen_labels.view(-1), reduction='none')
        rejected_loss = nn.functional.cross_entropy(rejected_logits.view(-1, rejected_logits.size(-1)), chosen_labels.view(-1), reduction='none')
        chosen_reward = -chosen_loss.sum(dim=-1)
        rejected_reward = -rejected_loss.sum(dim=-1)
        return chosen_reward, rejected_reward

    def train_step(self, chosen_inputs: Dict[str, torch.Tensor], rejected_inputs: Dict[str, torch.Tensor]) -> float:
        chosen_labels = chosen_inputs['labels']
        rejected_labels = rejected_inputs['labels']
        chosen_logits = self._compute_logits(self.model, chosen_inputs['input_ids'], chosen_inputs['attention_mask'], chosen_labels)
        rejected_logits = self._compute_logits(self.model, rejected_inputs['input_ids'], rejected_inputs['attention_mask'], rejected_labels)
        with torch.no_grad():
            ref_chosen_logits = self._compute_logits(self.ref_model, chosen_inputs['input_ids'], chosen_inputs['attention_mask'], chosen_labels)
            ref_rejected_logits = self._compute_logits(self.ref_model, rejected_inputs['input_ids'], rejected_inputs['attention_mask'], rejected_labels)
        chosen_reward, rejected_reward = self._compute_rewards(chosen_logits, rejected_logits, chosen_labels)
        ref_chosen_reward, ref_rejected_reward = self._compute_rewards(ref_chosen_logits, ref_rejected_logits, chosen_labels)
        chosen_advantage = chosen_reward - ref_chosen_reward
        rejected_advantage = rejected_reward - ref_rejected_reward
        loss = -nn.functional.logsigmoid(self.beta * (chosen_advantage - rejected_advantage)).mean()
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        return loss.item()
