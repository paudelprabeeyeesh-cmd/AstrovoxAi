"""API abuse detection with anomaly detection."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class MetricBaseline:
    metric_name: str
    mean: float
    std_dev: float
    sample_count: int = 0
    threshold_z: float = 3.0


@dataclass
class AnomalyAlert:
    metric_name: str
    value: float
    z_score: float
    severity: str
    user_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class APIAbuseDetector:
    """Detect API abuse using statistical anomaly detection."""

    def __init__(self):
        self._history: Dict[str, List[float]] = defaultdict(list)
        self._baselines: Dict[str, MetricBaseline] = {}
        self._alerts: List[AnomalyAlert] = []

    def record(self, user_id: str, metric_name: str, value: float) -> None:
        key = f"{user_id}:{metric_name}"
        self._history[key].append(value)
        if len(self._history[key]) > 1000:
            self._history[key] = self._history[key][-1000:]
        self._update_baseline(key, metric_name)

    def detect(self, user_id: str, metric_name: str, value: float) -> Optional[AnomalyAlert]:
        key = f"{user_id}:{metric_name}"
        baseline = self._baselines.get(key)
        if not baseline or baseline.sample_count < 10:
            return None
        z_score = (value - baseline.mean) / (baseline.std_dev if baseline.std_dev > 0 else 1.0)
        severity = "normal"
        if abs(z_score) > baseline.threshold_z:
            severity = "critical"
        elif abs(z_score) > 2.0:
            severity = "warning"
        if severity != "normal":
            alert = AnomalyAlert(
                metric_name=metric_name,
                value=value,
                z_score=z_score,
                severity=severity,
                user_id=user_id,
            )
            self._alerts.append(alert)
            logger.warning("API abuse alert: %s z=%.2f user=%s", metric_name, z_score, user_id)
            return alert
        return None

    def _update_baseline(self, key: str, metric_name: str) -> None:
        values = self._history[key][-100:]
        n = len(values)
        mean = sum(values) / n
        variance = sum((v - mean) ** 2 for v in values) / n
        std = variance ** 0.5
        self._baselines[key] = MetricBaseline(
            metric_name=metric_name,
            mean=mean,
            std_dev=std,
            sample_count=n,
        )

    def get_alerts(self, user_id: Optional[str] = None, limit: int = 100) -> List[AnomalyAlert]:
        alerts = self._alerts
        if user_id:
            alerts = [a for a in alerts if a.user_id == user_id]
        return alerts[-limit:]
