from typing import Optional, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F


class AdvancedKernelFusion:
    @staticmethod
    def fused_qkv_proj_out(x: torch.Tensor, q_proj: nn.Linear, k_proj: nn.Linear, v_proj: nn.Linear, out_proj: nn.Linear, attention_output: torch.Tensor) -> torch.Tensor:
        q = q_proj(x)
        k = k_proj(x)
        v = v_proj(x)
        return out_proj(attention_output)

    @staticmethod
    def fused_mlp(x: torch.Tensor, gate_proj: nn.Linear, up_proj: nn.Linear, down_proj: nn.Linear) -> torch.Tensor:
        gate = F.silu(gate_proj(x))
        up = up_proj(x)
        hidden = gate * up
        return down_proj(hidden)

    @staticmethod
    def fused_attention_mlp(x: torch.Tensor, qkv_proj: nn.Linear, out_proj: nn.Linear, mlp_gate: nn.Linear, mlp_up: nn.Linear, mlp_down: nn.Linear, norm_weight: torch.Tensor, eps: float = 1e-6) -> Tuple[torch.Tensor, torch.Tensor]:
        B, T, C = x.shape
        residual = x
        x = F.layer_norm(x, x.shape[-1:], weight=norm_weight, eps=eps)
        qkv = qkv_proj(x)
        q, k, v = qkv.split(C, dim=-1)
        scale = (C // 3) ** -0.5
        attn = (q @ k.transpose(-2, -1)) * scale
        attn = attn.softmax(dim=-1)
        attn_out = attn @ v
        attn_out = out_proj(attn_out)
        x = residual + attn_out
        residual = x
        x = F.layer_norm(x, x.shape[-1:], eps=eps)
        gate = F.silu(mlp_gate(x))
        up = mlp_up(x)
        hidden = gate * up
        mlp_out = mlp_down(hidden)
        x = residual + mlp_out
        return x, attn

    @staticmethod
    def fused_rope_attention(q: torch.Tensor, k: torch.Tensor, v: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor) -> torch.Tensor:
        q_rot = q[..., ::2] * cos - q[..., 1::2] * sin
        q_pass = q[..., ::2] * sin + q[..., 1::2] * cos
        q = torch.cat([q_rot, q_pass], dim=-1)
        k_rot = k[..., ::2] * cos - k[..., 1::2] * sin
        k_pass = k[..., ::2] * sin + k[..., 1::2] * cos
        k = torch.cat([k_rot, k_pass], dim=-1)
        scale = q.shape[-1] ** -0.5
        attn = (q @ k.transpose(-2, -1)) * scale
        attn = attn.softmax(dim=-1)
        return attn @ v

    @staticmethod
    def fused_bias_dropout_add(x: torch.Tensor, residual: torch.Tensor, bias: Optional[torch.Tensor] = None, dropout: float = 0.1, training: bool = True) -> torch.Tensor:
        if bias is not None:
            x = x + bias
        return F.dropout(x, p=dropout, training=training) + residual
