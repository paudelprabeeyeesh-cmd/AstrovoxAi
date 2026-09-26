"""A/B testing platform for model and feature experiments."""
from __future__ import annotations

import logging
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ABTestResult:
    test_id: str
    variant_a: str
    variant_b: str
    metric_a: float
    metric_b: float
    winner: Optional[str]
    confidence: float
    completed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ABTest:
    test_id: str
    name: str
    variant_a: str
    variant_b: str
    traffic_split: float = 0.5
    metric_fn: Optional[Callable[[Any], float]] = None
    status: str = "running"
    results: List[ABTestResult] = field(default_factory=list)


class ABTestManager:
    def __init__(self) -> None:
        self._tests: Dict[str, ABTest] = {}

    def create_test(self, test: ABTest) -> ABTest:
        self._tests[test.test_id] = test
        return test

    def assign_variant(self, test_id: str, user_id: str) -> str:
        test = self._tests.get(test_id)
        if not test:
            raise ValueError(f"Unknown test: {test_id}")
        return test.variant_a if random.random() < test.traffic_split else test.variant_b

    async def complete_test(self, test_id: str, metrics_a: List[float], metrics_b: List[float]) -> ABTestResult:
        test = self._tests.get(test_id)
        if not test:
            raise ValueError(f"Unknown test: {test_id}")
        avg_a = sum(metrics_a) / len(metrics_a) if metrics_a else 0.0
        avg_b = sum(metrics_b) / len(metrics_b) if metrics_b else 0.0
        winner = test.variant_a if avg_a > avg_b else test.variant_b if avg_b > avg_a else None
        result = ABTestResult(
            test_id=test_id,
            variant_a=test.variant_a,
            variant_b=test.variant_b,
            metric_a=avg_a,
            metric_b=avg_b,
            winner=winner,
            confidence=abs(avg_a - avg_b) / max(max(avg_a, avg_b), 1e-6),
        )
        test.results.append(result)
        test.status = "completed"
        return result


ab_test_manager = ABTestManager()
