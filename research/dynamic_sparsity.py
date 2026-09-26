import logging
from typing import Optional
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


class DynamicSparsityModule(nn.Module):
    def __init__(self, hidden_size: int, sparsity_threshold: float = 0.1):
        super().__init__()
        self.hidden_size = hidden_size
        self.sparsity_threshold = sparsity_threshold
        self.gate = nn.Linear(hidden_size, hidden_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        gate_logits = self.gate(x)
        gate_probs = torch.sigmoid(gate_logits)
        mask = (gate_probs > self.sparsity_threshold).float()
        return x * mask


class DynamicSparseTransformerBlock(nn.Module):
    def __init__(self, hidden_size: int, num_heads: int, intermediate_size: int, dropout: float = 0.1):
        super().__init__()
        self.attn = nn.MultiheadAttention(hidden_size, num_heads, dropout=dropout, batch_first=True)
        self.sparse = DynamicSparsityModule(hidden_size)
        self.ffn = nn.Sequential(
            nn.Linear(hidden_size, intermediate_size),
            nn.GELU(),
            nn.Linear(intermediate_size, hidden_size),
            nn.Dropout(dropout),
        )
        self.ln1 = nn.LayerNorm(hidden_size)
        self.ln2 = nn.LayerNorm(hidden_size)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        x = self.ln1(x)
        attn_out, _ = self.attn(x, x, x, attn_mask=mask)
        x = x + self.dropout(attn_out)
        x = x + self.dropout(self.ffn(self.ln2(x)))
        return self.sparse(x)
