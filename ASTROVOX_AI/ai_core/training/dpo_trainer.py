from typing import Optional, Dict, Any
import torch
import torch.nn as nn
import torch.nn.functional as F


class DPOTrainer:
    def __init__(self, model: nn.Module, reference_model: nn.Module, beta: float = 0.1, lr: float = 1e-5):
        self.model = model
        self.reference_model = reference_model
        self.beta = beta
        self.lr = lr
        self.optimizer = torch.optim.AdamW(model.parameters(), lr=lr)

    def dpo_loss(self, chosen_logits: torch.Tensor, rejected_logits: torch.Tensor, chosen_ref_logits: torch.Tensor, rejected_ref_logits: torch.Tensor) -> Tuple[torch.Tensor, Dict[str, float]]:
        chosen_logps = F.log_softmax(chosen_logits, dim=-1).gather(-1, chosen_logits.argmax(dim=-1, keepdim=True)).squeeze(-1)
        rejected_logps = F.log_softmax(rejected_logits, dim=-1).gather(-1, rejected_logits.argmax(dim=-1, keepdim=True)).squeeze(-1)
        chosen_ref_logps = F.log_softmax(chosen_ref_logits, dim=-1).gather(-1, chosen_ref_logits.argmax(dim=-1, keepdim=True)).squeeze(-1)
        rejected_ref_logps = F.log_softmax(rejected_ref_logits, dim=-1).gather(-1, rejected_ref_logits.argmax(dim=-1, keepdim=True)).squeeze(-1)
        logits_diff = self.beta * ((chosen_logps - chosen_ref_logps) - (rejected_logps - rejected_ref_logps))
        loss = -F.logsigmoid(logits_diff).mean()
        accuracy = (logits_diff > 0).float().mean()
        return loss, {'accuracy': accuracy.item()}

    def train_step(self, chosen_input_ids: torch.Tensor, rejected_input_ids: torch.Tensor) -> Dict[str, float]:
        chosen_logits = self.model(chosen_input_ids)
        rejected_logits = self.model(rejected_input_ids)
        with torch.no_grad():
            chosen_ref_logits = self.reference_model(chosen_input_ids)
            rejected_ref_logits = self.reference_model(rejected_input_ids)
        loss, metrics = self.dpo_loss(chosen_logits, rejected_logits, chosen_ref_logits, rejected_ref_logits)
        loss.backward()
        self.optimizer.step()
        self.optimizer.zero_grad()
        return {'loss': loss.item(), **metrics}
