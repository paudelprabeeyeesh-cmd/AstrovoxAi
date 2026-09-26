"""Real multi-model benchmarking lab."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from app.adapters.factory import get_adapter

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    provider: str
    model: str
    latency_ms: float
    tokens_used: int
    cost_usd: float
    success: bool
    error: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkSuite:
    prompt: str
    providers: list[str]
    runs: int = 3

    async def run(self) -> list[BenchmarkResult]:
        results: list[BenchmarkResult] = []
        for provider in self.providers:
            for _ in range(self.runs):
                result = await self._run_single(provider)
                results.append(result)
        return results

    async def _run_single(self, provider: str) -> BenchmarkResult:
        start = time.perf_counter()
        try:
            adapter = get_adapter(provider)
            response = await adapter.complete(self.prompt)
            latency_ms = (time.perf_counter() - start) * 1000
            return BenchmarkResult(
                provider=provider,
                model=getattr(adapter, "model", provider),
                latency_ms=latency_ms,
                tokens_used=response.get("usage", {}).get("total_tokens", 0),
                cost_usd=response.get("usage", {}).get("cost_usd", 0.0),
                success=True,
                metrics=response.get("metrics", {}),
            )
        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.error("Benchmark failed for %s: %s", provider, exc)
            return BenchmarkResult(
                provider=provider,
                model="unknown",
                latency_ms=latency_ms,
                tokens_used=0,
                cost_usd=0.0,
                success=False,
                error=str(exc),
            )

    def compare(self, results: list[BenchmarkResult]) -> dict[str, Any]:
        by_provider: dict[str, list[BenchmarkResult]] = {}
        for result in results:
            by_provider.setdefault(result.provider, []).append(result)
        comparison = {}
        for provider, provider_results in by_provider.items():
            successful = [r for r in provider_results if r.success]
            comparison[provider] = {
                "success_rate": len(successful) / max(len(provider_results), 1),
                "avg_latency_ms": sum(r.latency_ms for r in successful) / max(len(successful), 1),
                "avg_tokens": sum(r.tokens_used for r in successful) / max(len(successful), 1),
                "avg_cost_usd": sum(r.cost_usd for r in successful) / max(len(successful), 1),
            }
        return comparison
