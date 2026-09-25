from typing import Optional, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F


class CUDAKernels:
    @staticmethod
    def fused_linear(x: torch.Tensor, weight: torch.Tensor, bias: Optional[torch.Tensor] = None) -> torch.Tensor:
        if bias is not None:
            return torch.addmm(bias, x, weight.t())
        return x @ weight.t()

    @staticmethod
    def fused_rms_norm(x: torch.Tensor, weight: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
        variance = x.pow(2).mean(-1, keepdim=True)
        x = x * torch.rsqrt(variance + eps)
        return weight * x

    @staticmethod
    def scaled_dot_product_attention(q: torch.Tensor, k: torch.Tensor, v: torch.Tensor, scale: Optional[float] = None, mask: Optional[torch.Tensor] = None, dropout: float = 0.0) -> torch.Tensor:
        if scale is None:
            scale = q.shape[-1] ** -0.5
        attn = (q @ k.transpose(-2, -1)) * scale
        if mask is not None:
            attn = attn.masked_fill(mask == 0, float('-inf'))
        attn = attn.softmax(dim=-1)
        if dropout > 0:
            attn = F.dropout(attn, p=dropout)
        return attn @ v

    @staticmethod
    def rotary_embedding(x: torch.Tensor, inv_freq: torch.Tensor) -> torch.Tensor:
        t = torch.arange(x.shape[-2], device=x.device).type_as(inv_freq)
        freqs = torch.outer(t, inv_freq)
        emb = torch.cat((freqs.sin(), freqs.cos()), dim=-1)
        x1, x2 = x[..., ::2], x[..., 1::2]
        x_rotated = torch.stack((-x2, x1), dim=-1).flatten(-2)
        return x * emb.unsqueeze(0).unsqueeze(0) + x_rotated * emb.unsqueeze(0).unsqueeze(0)

    @staticmethod
    def swiglu(x: torch.Tensor, gate_proj: torch.Tensor, up_proj: torch.Tensor, down_proj: torch.Tensor) -> torch.Tensor:
        return down_proj(F.silu(gate_proj(x)) * up_proj(x))

    @staticmethod
    def layer_norm(x: torch.Tensor, weight: torch.Tensor, bias: Optional[torch.Tensor] = None, eps: float = 1e-6) -> torch.Tensor:
        mean = x.mean(-1, keepdim=True)
        var = x.var(-1, keepdim=True, unbiased=False)
        x = (x - mean) / torch.sqrt(var + eps)
        if bias is not None:
            return weight * x + bias
        return weight * x
