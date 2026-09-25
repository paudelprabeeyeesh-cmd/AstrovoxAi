from typing import Optional
import torch
import torch.nn as nn


class ALiBi(nn.Module):
    def __init__(self, num_heads: int, max_seq_len: int = 2048):
        super().__init__()
        self.num_heads = num_heads
        self.max_seq_len = max_seq_len
        slopes = torch.tensor([2 ** (-8 * (i + 1) / num_heads) for i in range(num_heads)])
        self.register_buffer('slopes', slopes, persistent=False)
        self.register_buffer('bias', self._build_bias(max_seq_len), persistent=False)

    def _build_bias(self, max_seq_len: int) -> torch.Tensor:
        context = torch.arange(max_seq_len, dtype=torch.float32).unsqueeze(0) - torch.arange(max_seq_len, dtype=torch.float32).unsqueeze(1)
        bias = -torch.abs(context).unsqueeze(0).unsqueeze(0)
        return bias

    def forward(self, attn: torch.Tensor, seq_len: Optional[int] = None) -> torch.Tensor:
        if seq_len is None:
            seq_len = attn.shape[-1]
        return attn + self.bias[:, :, :seq_len, :seq_len] * self.slopes.view(-1, 1, 1, 1)
