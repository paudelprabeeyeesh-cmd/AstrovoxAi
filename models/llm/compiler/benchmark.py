from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from models.llm.compiler.graph import ComputationGraph


@dataclass
class BenchmarkResult:
    backend: str
    elapsed_ms: float
    memory_bytes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class BenchmarkRunner:
    def __init__(self, warmup_runs: int = 2, runs: int = 5) -> None:
        self.warmup_runs = warmup_runs
        self.runs = runs

    def run(self, graph: ComputationGraph, backend: str) -> BenchmarkResult:
        for _ in range(self.warmup_runs):
            self._execute(graph, backend)
        start = time.perf_counter()
        for _ in range(self.runs):
            self._execute(graph, backend)
        elapsed = (time.perf_counter() - start) / self.runs * 1000.0
        return BenchmarkResult(backend=backend, elapsed_ms=elapsed, memory_bytes=0)

    def _execute(self, graph: ComputationGraph, backend: str) -> None:
        for node in graph.nodes.values():
            _ = node.op


class OptimizationTracker:
    def __init__(self) -> None:
        self.history: List[Dict[str, Any]] = []

    def record(self, baseline: BenchmarkResult, optimized: BenchmarkResult) -> Dict[str, Any]:
        entry = {
            "baseline_ms": baseline.elapsed_ms,
            "optimized_ms": optimized.elapsed_ms,
            "speedup": baseline.elapsed_ms / optimized.elapsed_ms if optimized.elapsed_ms > 0 else 0.0,
            "backend": optimized.backend,
        }
        self.history.append(entry)
        return entry


class BenchmarkComparison:
    def __init__(self, runner: BenchmarkRunner, tracker: OptimizationTracker) -> None:
        self.runner = runner
        self.tracker = tracker

    def compare(self, graph: ComputationGraph, backend: str) -> Dict[str, Any]:
        baseline = self.runner.run(graph, backend)
        from models.llm.compiler.optimizer import DeadCodeEliminator, FusionPass
        optimizer = FusionPass()
        opt_graph = optimizer.run(graph)
        opt_graph = DeadCodeEliminator().run(opt_graph)
        optimized = self.runner.run(opt_graph, backend)
        return self.tracker.record(baseline, optimized)
