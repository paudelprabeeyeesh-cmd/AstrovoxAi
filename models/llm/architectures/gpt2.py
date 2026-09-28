"""GPT-2 architecture reproduction from 'Language Models are Unsupervised Multitask Learners'."""

import logging
from typing import Any, Dict

import torch
import torch.nn as nn

from .base import ArchitectureSpec, BaseArchitecture

logger = logging.getLogger(__name__)


class GPT2Attention(nn.Module):
    def __init__(self, hidden_size: int, num_heads: int, dropout: float = 0.1, use_bias: bool = True):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_heads = num_heads
        self.head_dim = hidden_size // num_heads
        assert hidden_size % num_heads == 0

        self.c_attn = nn.Linear(hidden_size, 3 * hidden_size, bias=use_bias)
        self.c_proj = nn.Linear(hidden_size, hidden_size, bias=use_bias)
        self.attn_dropout = nn.Dropout(dropout)
        self.resid_dropout = nn.Dropout(dropout)
        self.use_bias = use_bias

    def forward(self, x: torch.Tensor, mask: torch.Tensor | None = None) -> torch.Tensor:
        B, T, C = x.size()
        q, k, v = self.c_attn(x).split(self.hidden_size, dim=2)
        q = q.view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        k = k.view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        v = v.view(B, T, self.num_heads, self.head_dim).transpose(1, 2)

        attn = torch.nn.functional.scaled_dot_product_attention(q, k, v, is_causal=True)
        attn = self.attn_dropout(attn)
        y = attn.transpose(1, 2).contiguous().view(B, T, C)
        y = self.resid_dropout(self.c_proj(y))
        return y


class GPT2MLP(nn.Module):
    def __init__(self, hidden_size: int, intermediate_size: int, dropout: float = 0.1, use_bias: bool = True):
        super().__init__()
        self.c_fc = nn.Linear(hidden_size, intermediate_size, bias=use_bias)
        self.c_proj = nn.Linear(intermediate_size, hidden_size, bias=use_bias)
        self.dropout = nn.Dropout(dropout)
        self.activation = nn.GELU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.c_fc(x)
        x = self.activation(x)
        x = self.c_proj(x)
        x = self.dropout(x)
        return x


class GPT2Block(nn.Module):
    def __init__(self, hidden_size: int, num_heads: int, intermediate_size: int, dropout: float = 0.1, use_bias: bool = True):
        super().__init__()
        self.ln_1 = nn.LayerNorm(hidden_size)
        self.attn = GPT2Attention(hidden_size, num_heads, dropout, use_bias)
        self.ln_2 = nn.LayerNorm(hidden_size)
        self.mlp = GPT2MLP(hidden_size, intermediate_size, dropout, use_bias)

    def forward(self, x: torch.Tensor, mask: torch.Tensor | None = None) -> torch.Tensor:
        x = x + self.attn(self.ln_1(x), mask)
        x = x + self.mlp(self.ln_2(x))
        return x


class GPT2Model(nn.Module):
    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.config = config
        self.hidden_size = config["hidden_size"]
        self.vocab_size = config["vocab_size"]
        self.num_layers = config["num_layers"]
        self.num_heads = config["num_heads"]
        self.intermediate_size = config["intermediate_size"]
        self.dropout = config.get("dropout", 0.1)
        self.use_bias = config.get("use_bias", True)
        self.tie_weights = config.get("tie_weights", True)

        self.wte = nn.Embedding(self.vocab_size, self.hidden_size)
        self.wpe = nn.Embedding(config.get("max_seq_len", 1024), self.hidden_size)
        self.drop = nn.Dropout(self.dropout)
        self.h = nn.ModuleList([
            GPT2Block(self.hidden_size, self.num_heads, self.intermediate_size, self.dropout, self.use_bias)
            for _ in range(self.num_layers)
        ])
        self.ln_f = nn.LayerNorm(self.hidden_size)
        self.lm_head = nn.Linear(self.hidden_size, self.vocab_size, bias=self.use_bias)
        if self.tie_weights:
            self.lm_head.weight = self.wte.weight

    def forward(self, input_ids: torch.Tensor, labels: torch.Tensor | None = None) -> Dict[str, torch.Tensor]:
        B, T = input_ids.size()
        pos = torch.arange(T, device=input_ids.device).unsqueeze(0)
        x = self.wte(input_ids) + self.wpe(pos)
        x = self.drop(x)
        for block in self.h:
            x = block(x)
        x = self.ln_f(x)
        logits = self.lm_head(x)
        loss = None
        if labels is not None:
            loss = torch.nn.functional.cross_entropy(logits.view(-1, logits.size(-1)), labels.view(-1))
        return {"logits": logits, "loss": loss}


class GPT2Architecture(BaseArchitecture):
    SPEC = ArchitectureSpec(
        name="gpt2",
        family="gpt",
        paper="Language Models are Unsupervised Multitask Learners (GPT-2)",
        description="Decoder-only transformer with LayerNorm, GELU, and no RoPE",
        config_path="models/llm/configs/config_gpt2.yaml",
        parameter_formula=" vocab*hidden + layers*(2*hidden + 4*hidden^2 + 2*hidden*ffn + hidden*ffn) + hidden",
        key_innovations=["large-scale web pretraining", "zero-shot task transfer", "no task-specific training"],
        supported_features=["causal_attention", "gelu_activation", "layer_norm", "weight_tying"],
    )

    def build(self, config: Dict[str, Any]) -> nn.Module:
        return GPT2Model(config)

    def count_parameters(self, config: Dict[str, Any]) -> int:
        vocab = config["vocab_size"]
        hidden = config["hidden_size"]
        layers = config["num_layers"]
        heads = config["num_heads"]
        ffn = config["intermediate_size"]
        use_bias = config.get("use_bias", True)
        head_dim = hidden // heads

        params = vocab * hidden  # token embeddings
        params += config.get("max_seq_len", 1024) * hidden  # position embeddings

        per_block = 0
        # LayerNorm: 2 LayerNorms per block, each with gamma + beta = 4 * hidden
        per_block += 4 * hidden
        # Attention: QKV + O projections
        per_block += 3 * hidden * hidden + hidden * hidden  # c_attn + c_proj
        # MLP: up + down projections
        per_block += hidden * ffn + ffn * hidden
        # Biases if used
        if use_bias:
            per_block += 5 * hidden + ffn  # c_attn (3*hidden) + c_proj_attn (hidden) + c_fc (ffn) + c_proj_mlp (hidden)

        params += layers * per_block
        params += 2 * hidden  # final LayerNorm (gamma + beta)

        # LM head weights (not tied if tie_weights=False)
        if not config.get("tie_weights", True):
            params += hidden * vocab
        # LM head bias always exists in GPT-2
        params += vocab

        return params

    def get_spec(self) -> ArchitectureSpec:
        return self.SPEC
