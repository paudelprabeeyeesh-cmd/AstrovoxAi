from typing import Optional
import torch
import torch.nn.functional as F

try:
    import triton
    import triton.language as tl
    TRITON_AVAILABLE = True
except ImportError:
    TRITON_AVAILABLE = False


if TRITON_AVAILABLE:
    def flash_attention_3_forward_triton(q: torch.Tensor, k: torch.Tensor, v: torch.Tensor, dropout_p: float = 0.0, causal: bool = True) -> torch.Tensor:
        return flash_attention_triton(q, k, v, causal=causal)


def flash_attention_3_forward(q: torch.Tensor, k: torch.Tensor, v: torch.Tensor, dropout_p: float = 0.0, causal: bool = True) -> torch.Tensor:
    if TRITON_AVAILABLE:
        return flash_attention_3_forward_triton(q, k, v, dropout_p, causal)
    scale = q.shape[-1] ** -0.5
    attn = (q @ k.transpose(-2, -1)) * scale
    if causal:
        T = q.shape[-2]
        causal_mask = torch.triu(torch.ones(T, T, device=q.device, dtype=torch.bool), diagonal=1)
        attn = attn.masked_fill(causal_mask.unsqueeze(0).unsqueeze(0), float('-inf'))
    attn = attn.softmax(dim=-1)
    if dropout_p > 0:
        attn = torch.nn.functional.dropout(attn, p=dropout_p)
    out = attn @ v
    return out
