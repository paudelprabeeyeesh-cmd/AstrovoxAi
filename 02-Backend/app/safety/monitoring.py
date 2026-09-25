"""Model behavior monitoring."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class BehaviorAlert:
    id: str
    model_id: str
    metric: str
    severity: str
    value: float
    threshold: float
    message: str
    timestamp: float = field(default_factory=time.time)


class ModelBehaviorMonitor:
    """Monitor AI model behavior for anomalies and degradation."""

    def __init__(self):
        self._metrics: dict[str, list[dict]] = {}
        self._alerts: list[BehaviorAlert] = []
        self._thresholds: dict[str, dict] = {}
        self._setup_defaults()

    def _setup_defaults(self):
        self._thresholds = {
            "response_time_ms": {"warning": 2000, "critical": 5000},
            "error_rate": {"warning": 0.05, "critical": 0.1},
            "safety_score": {"warning": 0.8, "critical": 0.6},
            "injection_detection_rate": {"warning": 0.9, "critical": 0.7},
            "jailbreak_detection_rate": {"warning": 0.95, "critical": 0.8},
            "pii_leak_rate": {"warning": 0.01, "critical": 0.05},
            "user_satisfaction": {"warning": 3.5, "critical": 3.0},
            "token_usage_per_request": {"warning": 4000, "critical": 8000},
        }

    def record_metric(self, model_id: str, metric_name: str, value: float, metadata: Optional[dict] = None):
        key = f"{model_id}:{metric_name}"
        entry = {
            "timestamp": time.time(),
            "model_id": model_id,
            "metric": metric_name,
            "value": value,
            "metadata": metadata or {},
        }
        self._metrics.setdefault(key, []).append(entry)
        self._check_threshold(model_id, metric_name, value)

    def _check_threshold(self, model_id: str, metric_name: str, value: float):
        thresholds = self._thresholds.get(metric_name)
        if not thresholds:
            return

        severity = None
        threshold_val = None
        if value <= thresholds.get("critical", float("inf")):
            severity = "critical"
            threshold_val = thresholds["critical"]
        elif value <= thresholds.get("warning", float("inf")):
            severity = "warning"
            threshold_val = thresholds["warning"]

        if severity:
            alert = BehaviorAlert(
                id=f"alert-{int(time.time()*1000)}",
                model_id=model_id,
                metric=metric_name,
                severity=severity,
                value=value,
                threshold=threshold_val,
                message=f"{metric_name} {severity}: {value} (threshold: {threshold_val})",
            )
            self._alerts.append(alert)
            logger.warning("ALERT %s: %s", severity, alert.message)

    def set_threshold(self, metric_name: str, warning: float, critical: float):
        self._thresholds[metric_name] = {"warning": warning, "critical": critical}

    def get_alerts(self, model_id: Optional[str] = None, severity: Optional[str] = None, limit: int = 100) -> list[BehaviorAlert]:
        alerts = self._alerts
        if model_id:
            alerts = [a for a in alerts if a.model_id == model_id]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        return alerts[-limit:]

    def get_metrics(self, model_id: str, metric_name: str, limit: int = 100) -> list[dict]:
        key = f"{model_id}:{metric_name}"
        return self._metrics.get(key, [])[-limit:]

    def get_metric_summary(self, model_id: str, metric_name: str) -> dict:
        entries = self.get_metrics(model_id, metric_name)
        if not entries:
            return {"model_id": model_id, "metric": metric_name, "count": 0}
        values = [e["value"] for e in entries]
        return {
            "model_id": model_id,
            "metric": metric_name,
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": round(sum(values) / len(values), 3),
            "latest": values[-1],
        }

    def get_model_health(self, model_id: str) -> dict:
        health = {}
        for metric_name in self._thresholds:
            summary = self.get_metric_summary(model_id, metric_name)
            health[metric_name] = summary
        model_alerts = [a for a in self._alerts if a.model_id == model_id]
        critical_alerts = [a for a in model_alerts if a.severity == "critical"]
        return {
            "model_id": model_id,
            "health": health,
            "alert_count": len(model_alerts),
            "critical_alerts": len(critical_alerts),
            "status": "degraded" if critical_alerts else ("warning" if model_alerts else "healthy"),
        }

    def detect_anomalies(self, model_id: str, metric_name: str, window: int = 20) -> list[dict]:
        entries = self.get_metrics(model_id, metric_name, limit=window)
        if len(entries) < 5:
            return []
        values = [e["value"] for e in entries]
        avg = sum(values) / len(values)
        variance = sum((v - avg) ** 2 for v in values) / len(values)
        std = variance ** 0.5
        anomalies = []
        for i, entry in enumerate(entries):
            if std > 0 and abs(entry["value"] - avg) > 2 * std:
                anomalies.append({
                    "index": i,
                    "timestamp": entry["timestamp"],
                    "value": entry["value"],
                    "avg": avg,
                    "std": std,
                    "deviation": abs(entry["value"] - avg) / std,
                })
        return anomalies


model_behavior_monitor = ModelBehaviorMonitor()
