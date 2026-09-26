"""Audit dashboard with metrics, aggregations, and real-time security posture."""
import logging
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)


@dataclass
class SecurityMetric:
    name: str
    value: float
    unit: str
    timestamp: float
    tags: Dict[str, str] = field(default_factory=dict)


class AuditDashboard:
    def __init__(self):
        self._metrics: List[SecurityMetric] = []
        self._events_by_severity: Dict[str, int] = defaultdict(int)
        self._events_by_action: Dict[str, int] = defaultdict(int)
        self._lock = __import__('threading').Lock()
        self._retention = 10000

    def record_metric(self, name: str, value: float, unit: str = "count", tags: Optional[Dict[str, str]] = None):
        metric = SecurityMetric(name=name, value=value, unit=unit, timestamp=time.time(), tags=tags or {})
        with self._lock:
            self._metrics.append(metric)
            if len(self._metrics) > self._retention:
                self._metrics = self._metrics[-self._retention:]
        logger.debug("Metric %s = %s %s", name, value, unit)

    def record_security_event(self, severity: str, action: str):
        with self._lock:
            self._events_by_severity[severity] += 1
            self._events_by_action[action] += 1

    def get_security_posture(self) -> Dict[str, Any]:
        with self._lock:
            recent = [m for m in self._metrics if time.time() - m.timestamp < 3600]
        return {
            "recent_metrics_count": len(recent),
            "total_metrics": len(self._metrics),
            "events_by_severity": dict(self._events_by_severity),
            "events_by_action": dict(self._events_by_action),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_top_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._lock:
            return sorted(self._events_by_action.items(), key=lambda x: x[1], reverse=True)[:limit]

    def get_metric_timeseries(self, metric_name: str, since: float = 3600) -> List[Dict[str, Any]]:
        cutoff = time.time() - since
        with self._lock:
            return [{"timestamp": m.timestamp, "value": m.value, "unit": m.unit} for m in self._metrics if m.name == metric_name and m.timestamp >= cutoff]


audit_dashboard = AuditDashboard()
