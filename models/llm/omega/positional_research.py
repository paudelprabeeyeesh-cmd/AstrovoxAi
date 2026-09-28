"""Omega-6: Positional encoding research with all major variants."""

import logging
import math
from dataclasses import dataclass

import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


@dataclass
class PositionalEncodingConfig:
    hidden_size: int = 768
    max_seq_len: int = 2048
    dropout: float = 0.1
    use_rope: bool = False
    use_alibi: bool = False
    use_learned: bool = False
    use_relative: bool = False
    num_buckets: int = 32
    max_distance: int = 128


class SinusoidalPositionalEncoding(nn.Module):
    def __init__(self, config: PositionalEncodingConfig):
        super().__init__()
        self.config = config
        pe = torch.zeros(config.max_seq_len, config.hidden_size)
        position = torch.arange(0, config.max_seq_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, config.hidden_size, 2).float() * (-math.log(10000.0) / config.hidden_size))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)
        self.register_buffer("pe", pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.pe[:, : x.size(1)]


class RoPEPositionalEncoding(nn.Module):
    def __init__(self, config: PositionalEncodingConfig):
        super().__init__()
        self.config = config
        inv_freq = 1.0 / (10000 ** (torch.arange(0, config.hidden_size, 2).float() / config.hidden_size))
        self.register_buffer("inv_freq", inv_freq)

    def forward(self, q: torch.Tensor, k: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        t = torch.arange(q.size(-2), device=q.device, dtype=self.inv_freq.dtype)
        freqs = torch.outer(t, self.inv_freq)
        emb = torch.cat([freqs, freqs], dim=-1)
        cos = emb.cos().unsqueeze(0).unsqueeze(0)
        sin = emb.sin().unsqueeze(0).unsqueeze(0)
        return self._apply_rotary_pos_emb(q, cos, sin), self._apply_rotary_pos_emb(k, cos, sin)

    @staticmethod
    def _apply_rotary_pos_emb(x: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor) -> torch.Tensor:
        x1, x2 = x.chunk(2, dim=-1)
        return torch.cat([x1 * cos - x2 * sin, x1 * sin + x2 * cos], dim=-1)


class ALiBiPositionalEncoding(nn.Module):
    def __init__(self, config: PositionalEncodingConfig):
        super().__init__()
        self.config = config
        self.num_heads = config.hidden_size // config.head_dim if hasattr(config, "head_dim") else 12
        slopes = torch.tensor([2 ** (-8 * (i + 1) / self.num_heads) for i in range(self.num_heads)])
        self.register_buffer("slopes", slopes)

    def forward(self, q: torch.Tensor, k: torch.Tensor) -> torch.Tensor:
        seq_len = q.size(-2)
        bias = -torch.abs(torch.arange(seq_len).unsqueeze(0) - torch.arange(seq_len).unsqueeze(1))
        return q, k


class LearnedPositionalEncoding(nn.Module):
    def __init__(self, config: PositionalEncodingConfig):
        super().__init__()
        self.config = config
        self.pe = nn.Embedding(config.max_seq_len, config.hidden_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        positions = torch.arange(x.size(1), device=x.device).unsqueeze(0)
        return x + self.pe(positions)


class RelativePositionalEncoding(nn.Module):
    def __init__(self, config: PositionalEncodingConfig):
        super().__init__()
        self.config = config
        self.embeddings = nn.Embedding(config.num_buckets, config.hidden_size)

    def forward(self, q: torch.Tensor, k: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        return q, k


class PositionalEncodingResearch:
    def __init__(self, config: PositionalEncodingConfig | None = None):
        self.config = config or PositionalEncodingConfig()
        self.encodings = {
            "sinusoidal": SinusoidalPositionalEncoding(self.config),
            "rope": RoPEPositionalEncoding(self.config),
            "alibi": ALiBiPositionalEncoding(self.config),
            "learned": LearnedPositionalEncoding(self.config),
            "relative": RelativePositionalEncoding(self.config),
        }

    def get_encoding(self, name: str) -> nn.Module:
        if name not in self.encodings:
            raise ValueError(f"Unknown positional encoding: {name}")
        return self.encodings[name]

    def benchmark(self, batch_size: int = 4, seq_len: int = 1024, hidden_size: int = 768) -> Dict[str, float]:
        x = torch.randn(batch_size, seq_len, hidden_size)
        results = {}
        for name, encoding in self.encodings.items():
            start = torch.cuda.Event(enable_timing=True) if torch.cuda.is_available() else None
            end = torch.cuda.Event(enable_timing=True) if torch.cuda.is_available() else None
            if torch.cuda.is_available():
                encoding = encoding.cuda()
                x = x.cuda()
                start.record()
                _ = encoding(x)
                end.record()
                torch.cuda.synchronize()
                results[name] = start.elapsed_time(end)
            else:
                import time
                s = time.perf_counter()
                _ = encoding(x)
                results[name] = (time.perf_counter() - s) * 1000
        return results
