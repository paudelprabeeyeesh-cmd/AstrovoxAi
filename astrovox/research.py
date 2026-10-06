"""Research evaluation framework for new papers and techniques.

Provides lightweight harnesses to evaluate whether a proposed idea should
be adopted into Astrovox core. Each experiment records inputs, config,
metrics, and a pass/fail recommendation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional


@dataclass(frozen=True)
class ExperimentConfig:
    name: str
    hypothesis: str = ""
    tags: List[str] = field(default_factory=list)
    max_minutes: int = 30


@dataclass
class ExperimentResult:
    config: ExperimentConfig
    passed: bool
    metrics: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class ExperimentHarness:
    def __init__(self, registry: Optional[Dict[str, ExperimentResult]] = None) -> None:
        self.registry = registry or {}

    def run(self, config: ExperimentConfig, fn: Callable[[], Dict[str, Any]]) -> ExperimentResult:
        metrics = {}
        passed = True
        try:
            metrics = fn() or {}
        except Exception as exc:
            passed = False
            metrics["error"] = str(exc)
        result = ExperimentResult(config=config, passed=passed, metrics=metrics)
        self.registry[config.name] = result
        return result

    def acceptance_rate(self) -> float:
        if not self.registry:
            return 0.0
        return sum(1 for result in self.registry.values() if result.passed) / len(self.registry)


def relative_latency(baseline_ms: float, candidate_ms: float) -> float:
    if baseline_ms <= 0:
        return 0.0
    return (candidate_ms - baseline_ms) / baseline_ms


def passes_threshold(regression: float, threshold: float = 0.10) -> bool:
    return regression <= threshold


def acceptance_rate(registry: Dict[str, ExperimentResult]) -> float:
    if not registry:
        return 0.0
    return sum(1 for result in registry.values() if result.passed) / len(registry)


def summarize(results: List[ExperimentResult]) -> Dict[str, Any]:
    return {
        "count": len(results),
        "passed": sum(1 for r in results if r.passed),
        "failed": sum(1 for r in results if not r.passed),
        "acceptance_rate": len(results) and sum(1 for r in results if r.passed) / len(results),
    }
