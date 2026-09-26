from typing import Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F


class Expert(nn.Module):
    def __init__(self, hidden_size: int, intermediate_size: int, dropout: float = 0.0):
        super().__init__()
        self.fc1 = nn.Linear(hidden_size, intermediate_size)
        self.fc2 = nn.Linear(intermediate_size, hidden_size)
        self.dropout = nn.Dropout(dropout)
        self.activation = nn.GELU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.fc2(self.dropout(self.activation(self.fc1(x))))


class MoELayer(nn.Module):
    def __init__(self, hidden_size: int, intermediate_size: int, num_experts: int, top_k: int = 2, dropout: float = 0.0):
        super().__init__()
        self.num_experts = num_experts
        self.top_k = top_k
        self.experts = nn.ModuleList([Expert(hidden_size, intermediate_size, dropout) for _ in range(num_experts)])
        self.gate = nn.Linear(hidden_size, num_experts, bias=False)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        B, T, C = x.shape
        x_flat = x.view(-1, C)
        logits = self.gate(x_flat)
        topk_logits, topk_indices = logits.topk(self.top_k, dim=-1)
        topk_probs = F.softmax(topk_logits, dim=-1)
        out = torch.zeros_like(x_flat)
        for i in range(self.top_k):
            expert_idx = topk_indices[:, i]
            expert_prob = topk_probs[:, i].unsqueeze(-1)
            for j in range(self.num_experts):
                mask = (expert_idx == j)
                if mask.any():
                    out[mask] += expert_prob[mask] * self.experts[j](x_flat[mask])
        return out.view(B, T, C), topk_probs
