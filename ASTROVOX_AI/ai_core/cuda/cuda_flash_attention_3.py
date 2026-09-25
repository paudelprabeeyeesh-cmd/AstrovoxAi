from typing import Optional
import torch


def flash_attention_3_forward(q: torch.Tensor, k: torch.Tensor, v: torch.Tensor, dropout_p: float = 0.0, causal: bool = True) -> torch.Tensor:
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
