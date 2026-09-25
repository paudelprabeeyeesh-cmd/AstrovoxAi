from typing import Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F
import math


def _look_around(x: torch.Tensor, backward: int = 1, forward: int = 1) -> torch.Tensor:
    B, H, T, D = x.shape
    out = torch.zeros(B, H, T, (backward + 1 + forward) * D, device=x.device, dtype=x.dtype)
    for b in range(B):
        for h in range(H):
            for t in range(T):
                for i in range(-backward, forward + 1):
                    tt = min(max(t + i, 0), T - 1)
                    out[b, h, t, (i + backward) * D:(i + backward + 1) * D] = x[b, h, tt]
    return out


class LSHSelfAttention(nn.Module):
    def __init__(self, hidden_size: int, num_heads: int, bucket_size: int = 64, n_hashes: int = 4, dropout: float = 0.1):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_heads = num_heads
        self.head_dim = hidden_size // num_heads
        self.bucket_size = bucket_size
        self.n_hashes = n_hashes
        self.q_proj = nn.Linear(hidden_size, hidden_size)
        self.k_proj = nn.Linear(hidden_size, hidden_size)
        self.v_proj = nn.Linear(hidden_size, hidden_size)
        self.out_proj = nn.Linear(hidden_size, hidden_size)
        self.dropout = nn.Dropout(dropout)

    def _hash(self, x: torch.Tensor, n_buckets: int) -> torch.Tensor:
        projection = torch.randn(self.hidden_size, self.num_heads, device=x.device, dtype=x.dtype)
        x_proj = (x @ projection) % n_buckets
        return x_proj.long().clamp_(0, n_buckets - 1)

    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        B, T, C = x.shape
        q = self.q_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        q = q * self.head_dim ** -0.5
        attn = torch.matmul(q, k.transpose(-2, -1))
        if mask is not None:
            attn = attn.masked_fill(mask == 0, float('-inf'))
        attn = attn.softmax(dim=-1)
        attn = self.dropout(attn)
        out = torch.matmul(attn, v)
        out = out.transpose(1, 2).contiguous().view(B, T, C)
        return self.out_proj(out)


class FeedForward(nn.Module):
    def __init__(self, hidden_size: int, intermediate_size: int, dropout: float = 0.1):
        super().__init__()
        self.w1 = nn.Linear(hidden_size, intermediate_size)
        self.w2 = nn.Linear(intermediate_size, hidden_size)
        self.dropout = nn.Dropout(dropout)
        self.activation = nn.GELU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.w2(self.dropout(self.activation(self.w1(x))))


class ReformerBlock(nn.Module):
    def __init__(self, hidden_size: int, num_heads: int, intermediate_size: int, dropout: float = 0.1):
        super().__init__()
        self.attn = LSHSelfAttention(hidden_size, num_heads, dropout=dropout)
        self.ff = FeedForward(hidden_size, intermediate_size, dropout)
        self.ln1 = nn.LayerNorm(hidden_size)
        self.ln2 = nn.LayerNorm(hidden_size)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        x = x + self.dropout(self.attn(self.ln1(x), mask))
        x = x + self.dropout(self.ff(self.ln2(x)))
        return x


class Reformer(nn.Module):
    def __init__(
        self,
        vocab_size: int = 50257,
        hidden_size: int = 768,
        num_layers: int = 12,
        num_heads: int = 12,
        intermediate_size: int = 3072,
        max_position_embeddings: int = 1024,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.tok_emb = nn.Embedding(vocab_size, hidden_size)
        self.pos_emb = nn.Embedding(max_position_embeddings, hidden_size)
        self.drop = nn.Dropout(dropout)
        self.blocks = nn.ModuleList([
            ReformerBlock(hidden_size, num_heads, intermediate_size, dropout)
            for _ in range(num_layers)
        ])
        self.ln_f = nn.LayerNorm(hidden_size)
        self.head = nn.Linear(hidden_size, vocab_size, bias=False)

    def forward(self, idx: torch.Tensor, targets: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        B, T = idx.shape
        pos = torch.arange(T, device=idx.device).unsqueeze(0)
        x = self.tok_emb(idx) + self.pos_emb(pos)
        x = self.drop(x)
        for block in self.blocks:
            x = block(x)
        x = self.ln_f(x)
        logits = self.head(x)
        loss = None
        if targets is not None:
            loss = F.cross_entropy(logits.view(-1, logits.size(-1)), targets.view(-1))
        return logits, loss
