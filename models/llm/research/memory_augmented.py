from __future__ import annotations

import math
from typing import Literal

import torch
import torch.nn as nn
import torch.nn.functional as F


# ---------------------------------------------------------------------------
# 1. External Memory
# ---------------------------------------------------------------------------


class ExternalMemory(nn.Module):
    """External key-value memory bank with attention-based read/write."""

    def __init__(
        self,
        memory_size: int = 1024,
        hidden_size: int = 768,
        num_heads: int = 8,
        device=None,
        dtype=None,
    ):
        super().__init__()
        if hidden_size % num_heads != 0:
            raise ValueError("hidden_size must be divisible by num_heads")
        self.memory_size = memory_size
        self.hidden_size = hidden_size
        self.num_heads = num_heads
        self.head_dim = hidden_size // num_heads
        self.memory_key = nn.Parameter(
            torch.randn(memory_size, hidden_size, device=device, dtype=dtype)
        )
        self.memory_value = nn.Parameter(
            torch.randn(memory_size, hidden_size, device=device, dtype=dtype)
        )
        self.q_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.k_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.v_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.o_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self._reset_parameters()

    def _reset_parameters(self):
        nn.init.normal_(self.memory_key, mean=0.0, std=0.02)
        nn.init.normal_(self.memory_value, mean=0.0, std=0.02)

    def read(self, hidden_states: torch.Tensor) -> torch.Tensor:
        B, T, C = hidden_states.shape
        q = self.q_proj(hidden_states).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(self.memory_key).unsqueeze(0).transpose(1, 2)
        v = self.v_proj(self.memory_value).unsqueeze(0).transpose(1, 2)
        scale = self.head_dim**-0.5
        attn = torch.matmul(q, k) * scale
        attn = F.softmax(attn, dim=-1, dtype=torch.float32).to(hidden_states.dtype)
        out = torch.matmul(attn, v).transpose(1, 2).contiguous().view(B, T, C)
        return self.o_proj(out)

    def write(self, hidden_states: torch.Tensor, momentum: float = 0.99) -> None:
        with torch.no_grad():
            update = hidden_states.mean(dim=(0, 1), keepdim=True)
            self.memory_key.data = momentum * self.memory_key.data + (1.0 - momentum) * update
            self.memory_value.data = (
                momentum * self.memory_value.data + (1.0 - momentum) * update
            )


# ---------------------------------------------------------------------------
# 2. Compressive Memory
# ---------------------------------------------------------------------------


class CompressiveMemory(nn.Module):
    """Compressive memory with token compression and reconstruction."""

    def __init__(
        self,
        hidden_size: int = 768,
        compression_ratio: int = 4,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.compression_ratio = compression_ratio
        self.compress = nn.Linear(
            hidden_size * compression_ratio, hidden_size, bias=False, device=device, dtype=dtype
        )
        self.expand = nn.Linear(
            hidden_size, hidden_size * compression_ratio, bias=False, device=device, dtype=dtype
        )
        self._reset_parameters()

    def _reset_parameters(self):
        nn.init.normal_(self.compress.weight, mean=0.0, std=0.02)
        nn.init.normal_(self.expand.weight, mean=0.0, std=0.02)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T, C = x.shape
        if self.compression_ratio > T:
            return x
        pad = (self.compression_ratio - T % self.compression_ratio) % self.compression_ratio
        if pad > 0:
            x = F.pad(x, (0, 0, 0, pad))
        grouped = x.view(B, -1, self.compression_ratio * C)
        compressed = self.compress(grouped)
        expanded = self.expand(compressed).view(B, -1, C)
        return expanded[:, :T, :]


# ---------------------------------------------------------------------------
# 3. Memory Network
# ---------------------------------------------------------------------------


class MemoryNetwork(nn.Module):
    """Differentiable memory network with read/write heads."""

    def __init__(
        self,
        input_size: int = 768,
        hidden_size: int = 768,
        memory_size: int = 128,
        memory_dim: int = 768,
        num_layers: int = 4,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.embed = nn.Linear(input_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.layers = nn.ModuleList(
            [
                nn.Sequential(
                    nn.LayerNorm(hidden_size, device=device, dtype=dtype),
                    nn.Linear(hidden_size, memory_dim, bias=False, device=device, dtype=dtype),
                )
                for _ in range(num_layers)
            ]
        )
        self.memory_key = nn.Parameter(
            torch.randn(memory_size, memory_dim, device=device, dtype=dtype)
        )
        self.memory_value = nn.Parameter(
            torch.randn(memory_size, memory_dim, device=device, dtype=dtype)
        )
        self.q_proj = nn.Linear(hidden_size, memory_dim, bias=False, device=device, dtype=dtype)
        self.k_proj = nn.Linear(hidden_size, memory_dim, bias=False, device=device, dtype=dtype)
        self.v_proj = nn.Linear(hidden_size, memory_dim, bias=False, device=device, dtype=dtype)
        self.out_proj = nn.Linear(memory_dim, hidden_size, bias=False, device=device, dtype=dtype)
        self._reset_parameters()

    def _reset_parameters(self):
        nn.init.normal_(self.memory_key, mean=0.0, std=0.02)
        nn.init.normal_(self.memory_value, mean=0.0, std=0.02)

    def read(self, x: torch.Tensor) -> torch.Tensor:
        q = self.q_proj(x)
        k = self.k_proj(self.memory_key).unsqueeze(0)
        v = self.v_proj(self.memory_value).unsqueeze(0)
        attn = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(q.size(-1))
        attn = F.softmax(attn, dim=-1)
        return self.out_proj(torch.matmul(attn, v))

    def write(self, x: torch.Tensor, momentum: float = 0.99) -> None:
        with torch.no_grad():
            update = x.mean(dim=(0, 1), keepdim=True)
            self.memory_key.data = momentum * self.memory_key.data + (1.0 - momentum) * update
            self.memory_value.data = (
                momentum * self.memory_value.data + (1.0 - momentum) * update
            )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.embed(x)
        for layer in self.layers:
            residual = x
            mem_out = self.read(layer(x))
            x = mem_out + residual
        return x


# ---------------------------------------------------------------------------
# 4. Memory-Augmented Transformer
# ---------------------------------------------------------------------------


class MemoryAugmentedTransformerBlock(nn.Module):
    """Transformer block with external memory integration."""

    def __init__(
        self,
        hidden_size: int = 768,
        num_attention_heads: int = 12,
        intermediate_size: int = 3072,
        memory_size: int = 1024,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.ln1 = nn.LayerNorm(hidden_size, device=device, dtype=dtype)
        self.attn = MemoryEfficientAttention(
            hidden_size=hidden_size,
            num_attention_heads=num_attention_heads,
            device=device,
            dtype=dtype,
        )
        self.ln2 = nn.LayerNorm(hidden_size, device=device, dtype=dtype)
        self.memory = ExternalMemory(
            memory_size=memory_size, hidden_size=hidden_size, num_heads=num_attention_heads,
            device=device, dtype=dtype,
        )
        self.ln3 = nn.LayerNorm(hidden_size, device=device, dtype=dtype)
        self.mlp = nn.Sequential(
            nn.Linear(hidden_size, intermediate_size, bias=False, device=device, dtype=dtype),
            nn.SiLU(),
            nn.Linear(intermediate_size, hidden_size, bias=False, device=device, dtype=dtype),
        )

    def forward(
        self,
        hidden_states: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        x = hidden_states + self.attn(self.ln1(hidden_states), attention_mask)
        mem_out = self.memory.read(self.ln2(x))
        x = x + mem_out
        x = x + self.mlp(self.ln3(x))
        return x


class MemoryAugmentedTransformer(nn.Module):
    """Full memory-augmented transformer model."""

    def __init__(
        self,
        vocab_size: int = 32000,
        hidden_size: int = 768,
        num_hidden_layers: int = 12,
        num_attention_heads: int = 12,
        intermediate_size: int = 3072,
        memory_size: int = 1024,
        max_position_embeddings: int = 2048,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.token_embedding = nn.Embedding(vocab_size, hidden_size, device=device, dtype=dtype)
        self.blocks = nn.ModuleList(
            [
                MemoryAugmentedTransformerBlock(
                    hidden_size=hidden_size,
                    num_attention_heads=num_attention_heads,
                    intermediate_size=intermediate_size,
                    memory_size=memory_size,
                    device=device,
                    dtype=dtype,
                )
                for _ in range(num_hidden_layers)
            ]
        )
        self.ln_f = nn.LayerNorm(hidden_size, device=device, dtype=dtype)
        self.lm_head = nn.Linear(hidden_size, vocab_size, bias=False, device=device, dtype=dtype)
        self._reset_parameters()

    def _reset_parameters(self):
        nn.init.normal_(self.token_embedding.weight, mean=0.0, std=0.02)
        nn.init.normal_(self.lm_head.weight, mean=0.0, std=0.02)

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        x = self.token_embedding(input_ids)
        for block in self.blocks:
            x = block(x, attention_mask=attention_mask)
        x = self.ln_f(x)
        return self.lm_head(x)
