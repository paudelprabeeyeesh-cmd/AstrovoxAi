"""Small causal Transformer implemented with PyTorch autograd."""

import math

import torch
import torch.nn.functional as functional
from torch import nn

from .config import TinyTransformerConfig


class TransformerBlock(nn.Module):
    def __init__(self, config: TinyTransformerConfig):
        super().__init__()
        width = config.hidden_size
        self.norm1 = nn.LayerNorm(width)
        self.attention = nn.MultiheadAttention(width, config.num_heads, dropout=config.dropout, batch_first=True)
        self.norm2 = nn.LayerNorm(width)
        self.feed_forward = nn.Sequential(
            nn.Linear(width, width * config.mlp_ratio),
            nn.GELU(),
            nn.Linear(width * config.mlp_ratio, width),
            nn.Dropout(config.dropout),
        )

    def forward(self, hidden: torch.Tensor, causal_mask: torch.Tensor) -> torch.Tensor:
        normed = self.norm1(hidden)
        attended, _ = self.attention(normed, normed, normed, attn_mask=causal_mask, need_weights=False)
        hidden = hidden + attended
        return hidden + self.feed_forward(self.norm2(hidden))


class TinyTransformer(nn.Module):
    """Random-initialized next-token model; not a production chat model."""

    def __init__(self, config: TinyTransformerConfig):
        super().__init__()
        self.config = config
        self.token_embedding = nn.Embedding(config.vocab_size, config.hidden_size)
        self.position_embedding = nn.Embedding(config.context_length, config.hidden_size)
        self.blocks = nn.ModuleList(TransformerBlock(config) for _ in range(config.num_layers))
        self.final_norm = nn.LayerNorm(config.hidden_size)
        self.output = nn.Linear(config.hidden_size, config.vocab_size, bias=False)
        self.apply(self._initialize)

    @staticmethod
    def _initialize(module: nn.Module) -> None:
        if isinstance(module, (nn.Linear, nn.Embedding)):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if isinstance(module, nn.Linear) and module.bias is not None:
                nn.init.zeros_(module.bias)

    @property
    def parameter_count(self) -> int:
        return sum(parameter.numel() for parameter in self.parameters())

    def forward(self, token_ids: torch.Tensor, labels: torch.Tensor | None = None) -> tuple[torch.Tensor, torch.Tensor | None]:
        if token_ids.ndim != 2 or token_ids.shape[1] < 1:
            raise ValueError("token_ids must have shape [batch, non-empty sequence]")
        if token_ids.shape[1] > self.config.context_length:
            raise ValueError("sequence is longer than configured context_length")
        positions = torch.arange(token_ids.shape[1], device=token_ids.device)
        hidden = self.token_embedding(token_ids) + self.position_embedding(positions)[None, :, :]
        mask = torch.triu(torch.ones(token_ids.shape[1], token_ids.shape[1], dtype=torch.bool, device=token_ids.device), diagonal=1)
        for block in self.blocks:
            hidden = block(hidden, mask)
        logits = self.output(self.final_norm(hidden))
        loss = None
        if labels is not None:
            if labels.shape != token_ids.shape:
                raise ValueError("labels must have the same shape as token_ids")
            loss = functional.cross_entropy(logits.reshape(-1, logits.shape[-1]), labels.reshape(-1))
        return logits, loss

    @torch.inference_mode()
    def generate(self, prompt_ids: torch.Tensor, max_new_tokens: int = 32, temperature: float = 1.0, top_k: int | None = None) -> torch.Tensor:
        if not isinstance(max_new_tokens, int) or max_new_tokens < 0:
            raise ValueError("max_new_tokens must be a non-negative integer")
        if not math.isfinite(temperature) or not 0.05 <= temperature <= 2.0:
            raise ValueError("temperature must be finite and between 0.05 and 2.0")
        if top_k is not None and (not isinstance(top_k, int) or not 1 <= top_k <= self.config.vocab_size):
            raise ValueError("top_k must be between 1 and vocab_size")
        if prompt_ids.ndim != 2 or prompt_ids.shape[1] == 0:
            raise ValueError("prompt_ids must have shape [batch, non-empty sequence]")
        output = prompt_ids
        was_training = self.training
        self.eval()
        for _ in range(max_new_tokens):
            context = output[:, -self.config.context_length :]
            logits, _ = self(context)
            next_logits = logits[:, -1, :] / temperature
            if top_k is not None:
                threshold = torch.topk(next_logits, top_k, dim=-1).values[:, -1, None]
                next_logits = next_logits.masked_fill(next_logits < threshold, float("-inf"))
            next_id = torch.multinomial(torch.softmax(next_logits, dim=-1), num_samples=1)
            output = torch.cat((output, next_id), dim=1)
        self.train(was_training)
        return output
