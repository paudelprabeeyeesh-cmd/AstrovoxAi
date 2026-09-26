from typing import Optional, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F


class SparseMoERouter(nn.Module):
    def __init__(self, hidden_size: int, num_experts: int, top_k: int = 2):
        super().__init__()
        self.num_experts = num_experts
        self.top_k = top_k
        self.gate = nn.Linear(hidden_size, num_experts, bias=False)
        self.expert_mask = None

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        logits = self.gate(x)
        topk_logits, topk_indices = logits.topk(self.top_k, dim=-1)
        topk_probs = F.softmax(topk_logits, dim=-1)
        self.expert_mask = torch.zeros_like(logits).scatter_(1, topk_indices, 1)
        return topk_probs, topk_indices, self.expert_mask


class SparseMoELayer(nn.Module):
    def __init__(self, hidden_size: int, intermediate_size: int, num_experts: int, top_k: int = 2):
        super().__init__()
        self.router = SparseMoERouter(hidden_size, num_experts, top_k)
        self.experts = nn.ModuleList([nn.Sequential(nn.Linear(hidden_size, intermediate_size), nn.GELU(), nn.Linear(intermediate_size, hidden_size)) for _ in range(num_experts)])
        self.top_k = top_k

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T, C = x.shape
        x_flat = x.view(-1, C)
        topk_probs, topk_indices, mask = self.router(x_flat)
        out = torch.zeros_like(x_flat)
        for i in range(self.num_experts):
            expert_input = x_flat * mask[:, i].unsqueeze(-1)
            out += self.experts[i](expert_input) * topk_probs[:, i % self.top_k].unsqueeze(-1)
        return out.view(B, T, C)
