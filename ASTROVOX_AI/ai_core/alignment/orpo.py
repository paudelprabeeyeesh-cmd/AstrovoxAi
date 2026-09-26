from typing import Dict
import torch
import torch.nn as nn
import logging

logger = logging.getLogger(__name__)


class ORPOTrainer:
    def __init__(self, model: nn.Module, lr: float = 1e-6, beta: float = 0.1):
        self.model = model
        self.lr = lr
        self.beta = beta
        self.optimizer = torch.optim.AdamW(model.parameters(), lr=lr)

    def train_step(self, chosen_inputs: Dict[str, torch.Tensor], rejected_inputs: Dict[str, torch.Tensor]) -> float:
        chosen_labels = chosen_inputs['labels']
        rejected_labels = rejected_inputs['labels']
        chosen_logits = self.model(input_ids=chosen_inputs['input_ids'], attention_mask=chosen_inputs['attention_mask'], labels=chosen_labels).logits
        rejected_logits = self.model(input_ids=rejected_inputs['input_ids'], attention_mask=rejected_inputs['attention_mask'], labels=rejected_labels).logits
        chosen_loss = nn.functional.cross_entropy(chosen_logits.view(-1, chosen_logits.size(-1)), chosen_labels.view(-1), reduction='none').sum(dim=-1)
        rejected_loss = nn.functional.cross_entropy(rejected_logits.view(-1, rejected_logits.size(-1)), rejected_labels.view(-1), reduction='none').sum(dim=-1)
        log_odds = self.beta * torch.log(torch.exp(-chosen_loss) / torch.exp(-rejected_loss))
        loss = -nn.functional.logsigmoid(log_odds).mean()
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        return loss.item()
