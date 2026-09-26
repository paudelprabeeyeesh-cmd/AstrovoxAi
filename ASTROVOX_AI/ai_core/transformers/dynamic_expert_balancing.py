from typing import Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F


class DynamicExpertBalancer(nn.Module):
    def __init__(self, num_experts: int, balance_loss_coef: float = 0.01):
        super().__init__()
        self.num_experts = num_experts
        self.balance_loss_coef = balance_loss_coef
        self.register_buffer('expert_counts', torch.zeros(num_experts))
        self.register_buffer('total_tokens', torch.tensor(1.0))

    def forward(self, topk_indices: torch.Tensor, topk_probs: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        self.expert_counts.zero_()
        for i in range(topk_indices.shape[-1]):
            self.expert_counts.scatter_add_(0, topk_indices[:, i], torch.ones_like(topk_indices[:, i], dtype=torch.float))
        self.total_tokens += topk_indices.numel()
        expert_prob = self.expert_counts / self.total_tokens
        uniform_prob = torch.ones_like(expert_prob) / self.num_experts
        balance_loss = self.balance_loss_coef * F.kl_div(expert_prob.log(), uniform_prob, reduction='batchmean')
        return balance_loss, expert_prob
