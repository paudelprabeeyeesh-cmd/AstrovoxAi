"""
Evaluation metrics and benchmark suite.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import torch

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    name: str
    latency_ms: float
    throughput: float
    memory_mb: float
    score: Optional[float] = None
    metadata: Dict[str, Any] = None


def compute_perplexity(logits: torch.Tensor, labels: torch.Tensor) -> float:
    """Compute perplexity from logits and labels."""
    shift_logits = logits[..., :-1, :].contiguous()
    shift_labels = labels[..., 1:].contiguous()
    loss = torch.nn.functional.cross_entropy(shift_logits.view(-1, shift_logits.size(-1)), shift_labels.view(-1))
    return float(torch.exp(loss).item())


def compute_accuracy(predictions: torch.Tensor, targets: torch.Tensor) -> float:
    """Compute token-level accuracy."""
    correct = (predictions == targets).float().sum()
    return float((correct / targets.numel()).item())


def compute_bleu(references: List[str], candidates: List[str], max_n: int = 4) -> float:
    """Compute BLEU score."""
    from collections import Counter
    def get_ngrams(tokens, n):
        return [tuple(tokens[i:i+n]) for i in range(len(tokens)-n+1)]
    scores = []
    for ref, cand in zip(references, candidates):
        ref_tokens = ref.lower().split()
        cand_tokens = cand.lower().split()
        if not cand_tokens:
            scores.append(0.0)
            continue
        precisions = []
        for n in range(1, max_n + 1):
            ref_ngrams = Counter(get_ngrams(ref_tokens, n))
            cand_ngrams = Counter(get_ngrams(cand_tokens, n))
            if not cand_ngrams:
                precisions.append(0.0)
                continue
            matches = sum(min(cand_ngrams[ng], ref_ngrams.get(ng, 0)) for ng in cand_ngrams)
            precisions.append(matches / sum(cand_ngrams.values()))
        bp = 1.0 if len(cand_tokens) > len(ref_tokens) else np.exp(1 - len(ref_tokens) / max(len(cand_tokens), 1))
        score = bp * np.exp(np.mean(np.log(np.array(precisions) + 1e-10)))
        scores.append(score)
    return float(np.mean(scores))


class BenchmarkSuite:
    """Benchmark suite for model evaluation."""

    def __init__(self):
        self.results: List[BenchmarkResult] = []

    def benchmark_inference(self, model, input_ids: torch.Tensor, name: str = "inference") -> BenchmarkResult:
        torch.cuda.reset_peak_memory_stats() if torch.cuda.is_available() else None
        start = time.perf_counter()
        with torch.no_grad():
            _ = model(input_ids)
        latency = (time.perf_counter() - start) * 1000
        mem_mb = torch.cuda.max_memory_allocated() / (1024 * 1024) if torch.cuda.is_available() else 0
        throughput = input_ids.shape[0] / (latency / 1000)
        result = BenchmarkResult(name=name, latency_ms=latency, throughput=throughput, memory_mb=mem_mb)
        self.results.append(result)
        return result

    def benchmark_throughput(self, model, batch_sizes: List[int], seq_len: int = 128) -> Dict[int, float]:
        throughputs = {}
        model.eval()
        for bs in batch_sizes:
            input_ids = torch.randint(0, 1000, (bs, seq_len))
            result = self.benchmark_inference(model, input_ids, name=f"bs_{bs}")
            throughputs[bs] = result.throughput
        return throughputs

    def get_summary(self) -> dict:
        if not self.results:
            return {}
        latencies = [r.latency_ms for r in self.results]
        return {
            "num_tests": len(self.results),
            "avg_latency_ms": round(np.mean(latencies), 2),
            "p50_latency_ms": round(np.percentile(latencies, 50), 2),
            "p95_latency_ms": round(np.percentile(latencies, 95), 2),
            "p99_latency_ms": round(np.percentile(latencies, 99), 2),
            "max_memory_mb": round(max(r.memory_mb for r in self.results), 2),
        }
