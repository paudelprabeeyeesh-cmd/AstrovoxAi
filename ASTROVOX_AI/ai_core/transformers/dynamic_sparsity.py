import logging
from typing import Optional
import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


class DynamicSparsityModule(nn.Module):
    def __init__(self, hidden_size: int, sparsity_threshold: float = 0.1):
        super().__init__()
        self.hidden_size = hidden_size
        self.sparsity_threshold = sparsity_threshold
        self.gate = nn.Linear(hidden_size, hidden_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T, C = x.shape
        gate_logits = self.gate(x)
        gate_probs = torch.sigmoid(gate_logits)
        mask = (gate_probs > self.sparsity_threshold).float()
        return x * mask
