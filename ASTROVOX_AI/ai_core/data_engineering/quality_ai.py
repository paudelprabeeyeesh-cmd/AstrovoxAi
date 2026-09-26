"""AI data quality."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class QualityMetric:
    metric_name: str
    value: float
    threshold: float
    passed: bool


class AIDataQuality:
    def __init__(self) -> None:
        self._metrics: List[QualityMetric] = []

    def evaluate(self, metric_name: str, value: float, threshold: float) -> QualityMetric:
        metric = QualityMetric(metric_name=metric_name, value=value, threshold=threshold, passed=value >= threshold)
        self._metrics.append(metric)
        return metric

    def get_metrics(self) -> List[QualityMetric]:
        return list(self._metrics)


ai_data_quality = AIDataQuality()
