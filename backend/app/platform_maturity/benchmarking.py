"""Benchmarking for platform maturity."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkMetric:
    name: str
    value: float
    target: float
    unit: str


@dataclass
class BenchmarkComparison:
    comparison_id: str
    metric: str
    our_value: float
    industry_avg: float
    best_in_class: float
    gap: float = 0.0


class BenchmarkComparisonManager:
    def __init__(self) -> None:
        self._comparisons: List[BenchmarkComparison] = []

    def compare(self, metric: str, our_value: float, industry_avg: float, best_in_class: float) -> BenchmarkComparison:
        comparison = BenchmarkComparison(
            comparison_id=metric,
            metric=metric,
            our_value=our_value,
            industry_avg=industry_avg,
            best_in_class=best_in_class,
            gap=best_in_class - our_value,
        )
        self._comparisons.append(comparison)
        return comparison


benchmark_comparison_manager = BenchmarkComparisonManager()
