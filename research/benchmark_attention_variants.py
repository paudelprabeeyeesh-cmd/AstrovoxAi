import logging
import time
from dataclasses import dataclass
from typing import Optional
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    name: str
    latency_ms: float
    memory_mb: float
    throughput: float
    flops: Optional[int] = None


class BenchmarkAttentionVariants:
    def __init__(self, hidden_size: int = 768, num_heads: int = 12, seq_len: int = 1024):
        self.hidden_size = hidden_size
        self.num_heads = num_heads
        self.seq_len = seq_len
        self.head_dim = hidden_size // num_heads
        self.scale = self.head_dim ** -0.5

    def _make_inputs(self, batch_size: int = 2):
        return torch.randn(batch_size, self.seq_len, self.hidden_size)

    def _mask(self, T: int, batch_size: int = 2):
        return torch.tril(torch.ones(batch_size, 1, T, T))

    def benchmark_mha(self, x: torch.Tensor, mask: Optional[torch.Tensor]) -> BenchmarkResult:
        mha = nn.MultiheadAttention(self.hidden_size, self.num_heads, batch_first=True)
        torch.cuda.synchronize() if torch.cuda.is_available() else None
        start = time.perf_counter()
        _ = mha(x, x, x, attn_mask=mask.squeeze(1) if mask is not None else None)
        torch.cuda.synchronize() if torch.cuda.is_available() else None
        latency = (time.perf_counter() - start) * 1000
        return BenchmarkResult(
            name="MultiheadAttention",
            latency_ms=latency,
            memory_mb=x.element_size() * x.nelement() / (1024 * 1024),
            throughput=x.numel() / (latency / 1000),
        )

    def benchmark_gqa(self, x: torch.Tensor, mask: Optional[torch.Tensor]) -> BenchmarkResult:
        from ASTROVOX_AI.ai_core.research.gqa import GroupedQueryAttention
        gqa = GroupedQueryAttention(self.hidden_size, self.num_heads, self.num_heads // 2)
        torch.cuda.synchronize() if torch.cuda.is_available() else None
        start = time.perf_counter()
        _ = gqa(x, mask)
        torch.cuda.synchronize() if torch.cuda.is_available() else None
        latency = (time.perf_counter() - start) * 1000
        return BenchmarkResult(
            name="GroupedQueryAttention",
            latency_ms=latency,
            memory_mb=x.element_size() * x.nelement() / (1024 * 1024),
            throughput=x.numel() / (latency / 1000),
        )

    def benchmark_mqa(self, x: torch.Tensor, mask: Optional[torch.Tensor]) -> BenchmarkResult:
        from ASTROVOX_AI.ai_core.research.mqa import MultiQueryAttention
        mqa = MultiQueryAttention(self.hidden_size, self.num_heads)
        torch.cuda.synchronize() if torch.cuda.is_available() else None
        start = time.perf_counter()
        _ = mqa(x, mask)
        torch.cuda.synchronize() if torch.cuda.is_available() else None
        latency = (time.perf_counter() - start) * 1000
        return BenchmarkResult(
            name="MultiQueryAttention",
            latency_ms=latency,
            memory_mb=x.element_size() * x.nelement() / (1024 * 1024),
            throughput=x.numel() / (latency / 1000),
        )

    def benchmark_flash(self, x: torch.Tensor, mask: Optional[torch.Tensor]) -> BenchmarkResult:
        flash = nn.MultiheadAttention(self.hidden_size, self.num_heads, batch_first=True)
        torch.cuda.synchronize() if torch.cuda.is_available() else None
        start = time.perf_counter()
        _ = flash(x, x, x, attn_mask=mask.squeeze(1) if mask is not None else None)
        torch.cuda.synchronize() if torch.cuda.is_available() else None
        latency = (time.perf_counter() - start) * 1000
        return BenchmarkResult(
            name="FlashAttention",
            latency_ms=latency,
            memory_mb=x.element_size() * x.nelement() / (1024 * 1024),
            throughput=x.numel() / (latency / 1000),
        )

    def run_all(self) -> None:
        x = self._make_inputs()
        mask = self._mask(self.seq_len)
        variants = [
            self.benchmark_mha(x, mask),
            self.benchmark_gqa(x, mask),
            self.benchmark_mqa(x, mask),
            self.benchmark_flash(x, mask),
        ]
        logger.info("Attention benchmark results:")
        for result in variants:
            logger.info(
                "%s: latency=%.3fms throughput=%.0f tokens/s memory=%.2fMB",
                result.name,
                result.latency_ms,
                result.throughput,
                result.memory_mb,
            )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    BenchmarkAttentionVariants().run_all()
