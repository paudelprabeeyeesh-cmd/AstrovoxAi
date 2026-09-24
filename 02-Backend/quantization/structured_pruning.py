"""
Structured Pruning: remove attention heads, layers, or experts based on importance scores.
"""

from __future__ import annotations

from typing import List

import torch
import torch.nn as nn


def prune_attention_heads(model: nn.Module, head_importance: List[float], num_heads_to_keep: int) -> nn.Module:
    """Prune attention heads in all MultiheadAttention layers by importance scores."""
    if num_heads_to_keep <= 0:
        raise ValueError("num_heads_to_keep must be positive")
    keep_indices = sorted(range(len(head_importance)), key=lambda i: head_importance[i], reverse=True)[:num_heads_to_keep]
    keep_indices = sorted(keep_indices)
    for module in model.modules():
        if isinstance(module, nn.MultiheadAttention):
            embed_dim = module.embed_dim
            num_heads = module.num_heads
            head_dim = embed_dim // num_heads
            in_proj_weight = module.in_proj_weight
            in_proj_bias = module.in_proj_bias
            q_weight, k_weight, v_weight = torch.split(in_proj_weight, embed_dim, dim=0)
            if in_proj_bias is not None:
                q_bias, k_bias, v_bias = torch.split(in_proj_bias, embed_dim, dim=0)
            else:
                q_bias = k_bias = v_bias = None
            new_q, new_k, new_v = [], [], []
            new_qb, new_kb, new_vb = [], [], []
            for idx in keep_indices:
                start = idx * head_dim
                end = start + head_dim
                new_q.append(q_weight[start:end])
                new_k.append(k_weight[start:end])
                new_v.append(v_weight[start:end])
                if q_bias is not None:
                    new_qb.append(q_bias[start:end])
                    new_kb.append(k_bias[start:end])
                    new_vb.append(v_bias[start:end])
            new_q_weight = torch.cat(new_q, dim=0)
            new_k_weight = torch.cat(new_k, dim=0)
            new_v_weight = torch.cat(new_v, dim=0)
            new_in_proj_weight = torch.cat([new_q_weight, new_k_weight, new_v_weight], dim=0)
            new_in_proj_bias = None
            if q_bias is not None:
                new_q_bias = torch.cat(new_qb, dim=0)
                new_k_bias = torch.cat(new_kb, dim=0)
                new_v_bias = torch.cat(new_vb, dim=0)
                new_in_proj_bias = torch.cat([new_q_bias, new_k_bias, new_v_bias], dim=0)
            module.num_heads = len(keep_indices)
            module.embed_dim = len(keep_indices) * head_dim
            module.in_proj_weight = nn.Parameter(new_in_proj_weight)
            module.in_proj_bias = nn.Parameter(new_in_proj_bias) if new_in_proj_bias is not None else None
    return model


def prune_layers_by_importance(model: nn.Module, layer_importance: List[float], num_layers_to_keep: int) -> nn.Module:
    """Prune transformer layers by importance scores."""
    if num_layers_to_keep <= 0:
        raise ValueError("num_layers_to_keep must be positive")
    keep_indices = sorted(range(len(layer_importance)), key=lambda i: layer_importance[i], reverse=True)[:num_layers_to_keep]
    keep_indices = sorted(keep_indices)
    for name, module in list(model.named_children()):
        if isinstance(module, nn.ModuleList):
            new_layers = nn.ModuleList([module[i] for i in keep_indices])
            setattr(model, name, new_layers)
    return model


def prune_moe_experts(model: nn.Module, expert_importance: List[float], num_experts_to_keep: int) -> nn.Module:
    """Prune MoE experts by importance scores."""
    if num_experts_to_keep <= 0:
        raise ValueError("num_experts_to_keep must be positive")
    keep_indices = sorted(range(len(expert_importance)), key=lambda i: expert_importance[i], reverse=True)[:num_experts_to_keep]
    keep_indices = sorted(keep_indices)
    for module in model.modules():
        if hasattr(module, "experts") and isinstance(module.experts, (list, nn.ModuleList)):
            if isinstance(module.experts, nn.ModuleList):
                module.experts = nn.ModuleList([module.experts[i] for i in keep_indices])
            else:
                module.experts = [module.experts[i] for i in keep_indices]
            if hasattr(module, "num_experts"):
                module.num_experts = len(keep_indices)
    return model
