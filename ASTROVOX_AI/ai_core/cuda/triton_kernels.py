from typing import Optional
import torch
import torch.nn as nn
import torch.nn.functional as F


class TritonKernels:
    @staticmethod
    def fused_layer_norm_linear(x: torch.Tensor, weight: torch.Tensor, bias: Optional[torch.Tensor] = None, eps: float = 1e-6) -> torch.Tensor:
        out = F.layer_norm(x, x.shape[-1:], eps=eps)
        return torch.addmm(bias if bias is not None else torch.zeros(weight.size(0), device=x.device, dtype=x.dtype), out, weight.t())

    @staticmethod
    def fused_rms_norm_linear(x: torch.Tensor, weight: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
        variance = x.pow(2).mean(-1, keepdim=True)
        x = x * torch.rsqrt(variance + eps)
        return weight * x

    @staticmethod
    def fused_swiglu(x: torch.Tensor, gate_weight: torch.Tensor, up_weight: torch.Tensor, down_weight: torch.Tensor) -> torch.Tensor:
        gate = F.linear(x, gate_weight)
        up = F.linear(x, up_weight)
        hidden = F.silu(gate) * up
        return F.linear(hidden, down_weight)

    @staticmethod
    def fused_attn_qkv_proj(x: torch.Tensor, q_proj: nn.Linear, k_proj: nn.Linear, v_proj: nn.Linear) -> tuple:
        return q_proj(x), k_proj(x), v_proj(x)

    @staticmethod
    def fused_dropout_residual_add(x: torch.Tensor, residual: torch.Tensor, dropout: float = 0.1, training: bool = True) -> torch.Tensor:
        return F.dropout(x, p=dropout, training=training) + residual
