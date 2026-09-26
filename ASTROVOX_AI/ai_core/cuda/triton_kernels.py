from typing import Optional
import torch
import torch.nn as nn
import torch.nn.functional as F

try:
    TRITON_AVAILABLE = True
except ImportError:
    TRITON_AVAILABLE = False


class TritonKernels:
    @staticmethod
    def fused_layer_norm_linear(x: torch.Tensor, weight: torch.Tensor, bias: Optional[torch.Tensor] = None, eps: float = 1e-6) -> torch.Tensor:
        if TRITON_AVAILABLE:
            try:
                from ASTROVOX_AI.ai_core.cuda.cuda_layernorm import layer_norm_triton
                out = layer_norm_triton(x, weight, bias, eps)
                return out
            except ImportError:
                pass
        out = F.layer_norm(x, x.shape[-1:], weight=weight, bias=bias, eps=eps)
        if bias is not None:
            return torch.addmm(bias, out, weight.t())
        return out @ weight.t()

    @staticmethod
    def fused_rms_norm_linear(x: torch.Tensor, weight: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
        if TRITON_AVAILABLE:
            try:
                from ASTROVOX_AI.ai_core.cuda.cuda_rmsnorm import rms_norm_triton
                out = rms_norm_triton(x, weight, eps)
                return out
            except ImportError:
                pass
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

    @staticmethod
    def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
        if TRITON_AVAILABLE:
            try:
                from ASTROVOX_AI.ai_core.cuda.cuda_matmul import matmul_triton
                return matmul_triton(a, b)
            except ImportError:
                pass
        return torch.matmul(a, b)

    @staticmethod
    def softmax(x: torch.Tensor, dim: int = -1) -> torch.Tensor:
        if TRITON_AVAILABLE:
            try:
                from ASTROVOX_AI.ai_core.cuda.cuda_softmax import softmax_triton
                return softmax_triton(x, dim)
            except ImportError:
                pass
        return torch.softmax(x, dim=dim)

    @staticmethod
    def layer_norm(x: torch.Tensor, weight: torch.Tensor, bias: Optional[torch.Tensor] = None, eps: float = 1e-6) -> torch.Tensor:
        if TRITON_AVAILABLE:
            try:
                from ASTROVOX_AI.ai_core.cuda.cuda_layernorm import layer_norm_triton
                return layer_norm_triton(x, weight, bias, eps)
            except ImportError:
                pass
        mean = x.mean(-1, keepdim=True)
        var = x.var(-1, keepdim=True, unbiased=False)
        x = (x - mean) / torch.sqrt(var + eps)
        if bias is not None:
            return weight * x + bias
        return weight * x

    @staticmethod
    def rms_norm(x: torch.Tensor, weight: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
        if TRITON_AVAILABLE:
            try:
                from ASTROVOX_AI.ai_core.cuda.cuda_rmsnorm import rms_norm_triton
                return rms_norm_triton(x, weight, eps)
            except ImportError:
                pass
        variance = x.pow(2).mean(-1, keepdim=True)
        x = x * torch.rsqrt(variance + eps)
        return weight * x

    @staticmethod
    def flash_attention(q: torch.Tensor, k: torch.Tensor, v: torch.Tensor, causal: bool = True) -> torch.Tensor:
        if TRITON_AVAILABLE:
            try:
                from ASTROVOX_AI.ai_core.cuda.cuda_attention import flash_attention_triton
                return flash_attention_triton(q, k, v, causal=causal)
            except ImportError:
                pass
        scale = q.shape[-1] ** -0.5
        attn = (q @ k.transpose(-2, -1)) * scale
        if causal:
            T = q.shape[-2]
            causal_mask = torch.triu(torch.ones(T, T, device=q.device, dtype=torch.bool), diagonal=1)
            attn = attn.masked_fill(causal_mask.unsqueeze(0).unsqueeze(0), float('-inf'))
        attn = attn.softmax(dim=-1)
        out = attn @ v
        return out
