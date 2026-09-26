"""Productivity metrics collection."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ProductivityMetrics:
    user_id: str
    commits: int
    prs_opened: int
    prs_merged: int
    issues_resolved: int
    period_start: datetime
    period_end: datetime


class MetricsCollector:
    def __init__(self) -> None:
        self._metrics: List[ProductivityMetrics] = []

    def record(self, metrics: ProductivityMetrics) -> None:
        self._metrics.append(metrics)

    def get_user_metrics(self, user_id: str) -> List[ProductivityMetrics]:
        return [m for m in self._metrics if m.user_id == user_id]


metrics_collector = MetricsCollector()
