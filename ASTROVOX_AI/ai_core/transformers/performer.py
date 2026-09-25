from typing import Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F
import math


def ortho_matrix(d: int, device: torch.device, dtype: torch.dtype) -> torch.Tensor:
    m = torch.randn(d, d, device=device, dtype=dtype)
    q, _ = torch.linalg.qr(m)
    return q


class FeatureMap(nn.Module):
    def __init__(self, head_dim: int, nb_features: int = 256):
        super().__init__()
        self.head_dim = head_dim
        self.nb_features = nb_features
        self.register_buffer('ortho', ortho_matrix(head_dim, torch.device('cpu'), torch.float32))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, H, T, D = x.shape
        x_proj = x @ self.ortho.to(x.device, x.dtype).T
        return torch.cat([torch.cos(math.pi / 2 * x_proj), torch.sin(math.pi / 2 * x_proj)], dim=-1)


class PerformerAttention(nn.Module):
    def __init__(self, hidden_size: int, num_heads: int, nb_features: int = 256, dropout: float = 0.1):
        super().__init__()
        self.num_heads = num_heads
        self.head_dim = hidden_size // num_heads
        self.nb_features = nb_features
        self.q_proj = nn.Linear(hidden_size, hidden_size)
        self.k_proj = nn.Linear(hidden_size, hidden_size)
        self.v_proj = nn.Linear(hidden_size, hidden_size)
        self.out_proj = nn.Linear(hidden_size, hidden_size)
        self.feature_map = FeatureMap(self.head_dim, nb_features)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        B, T, C = x.shape
        q = self.q_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        q_prime = self.feature_map(q)
        k_prime = self.feature_map(k)
        q_norm = q_prime.norm(dim=-1, keepdim=True).clamp_min(1e-6)
        k_norm = k_prime.norm(dim=-1, keepdim=True).clamp_min(1e-6)
        q_prime = q_prime / q_norm
        k_prime = k_prime / k_norm
        kv = torch.matmul(k_prime.transpose(-2, -1), v)
        z = k_prime.sum(dim=-2, keepdim=True).clamp_min(1e-6)
        out = torch.matmul(q_prime, kv) / z
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


class PerformerBlock(nn.Module):
    def __init__(self, hidden_size: int, num_heads: int, intermediate_size: int, nb_features: int = 256, dropout: float = 0.1):
        super().__init__()
        self.attn = PerformerAttention(hidden_size, num_heads, nb_features, dropout)
        self.ff = FeedForward(hidden_size, intermediate_size, dropout)
        self.ln1 = nn.LayerNorm(hidden_size)
        self.ln2 = nn.LayerNorm(hidden_size)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        x = x + self.dropout(self.attn(self.ln1(x), mask))
        x = x + self.dropout(self.ff(self.ln2(x)))
        return x


class Performer(nn.Module):
    def __init__(
        self,
        vocab_size: int = 50257,
        hidden_size: int = 768,
        num_layers: int = 12,
        num_heads: int = 12,
        intermediate_size: int = 3072,
        max_position_embeddings: int = 1024,
        nb_features: int = 256,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.tok_emb = nn.Embedding(vocab_size, hidden_size)
        self.pos_emb = nn.Embedding(max_position_embeddings, hidden_size)
        self.drop = nn.Dropout(dropout)
        self.blocks = nn.ModuleList([
            PerformerBlock(hidden_size, num_heads, intermediate_size, nb_features, dropout)
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
