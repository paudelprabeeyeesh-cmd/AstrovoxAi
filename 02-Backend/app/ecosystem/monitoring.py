"""Ecosystem monitoring: plugin usage, API analytics, integration health."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Deque, Dict, Iterable, List, Optional

from ..logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class Event:
    name: str
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class EcosystemMonitor:
    """Lightweight in-memory metrics aggregator for ecosystem components."""

    def __init__(self, retention: int = 5000) -> None:
        self._events: Deque[Event] = deque(maxlen=retention)
        self._counters: Dict[str, int] = defaultdict(int)
        self._per_plugin: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._per_integration: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._per_endpoint: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._costs: Dict[str, float] = defaultdict(float)
        self._errors: Dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()

    def record(
        self,
        name: str,
        payload: Optional[Dict[str, Any]] = None,
        *,
        plugin_id: Optional[str] = None,
        integration: Optional[str] = None,
        endpoint: Optional[str] = None,
        cost: float = 0.0,
        error: Optional[str] = None,
    ) -> None:
        payload = dict(payload or {})
        if error is not None and "error" not in payload:
            payload["error"] = error
        with self._lock:
            self._events.append(Event(name=name, payload=payload))
            self._counters[name] += 1
            if plugin_id:
                self._per_plugin[plugin_id][name] += 1
            if integration:
                self._per_integration[integration][name] += 1
            if endpoint:
                self._per_endpoint[endpoint][name] += 1
            if cost:
                self._costs[name] += cost
            if payload.get("error"):
                self._errors[str(payload["error"])] += 1

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_events": len(self._events),
                "event_counts": dict(self._counters),
                "plugins": {k: dict(v) for k, v in self._per_plugin.items()},
                "integrations": {k: dict(v) for k, v in self._per_integration.items()},
                "endpoints": {k: dict(v) for k, v in self._per_endpoint.items()},
                "costs": {k: round(v, 4) for k, v in self._costs.items()},
                "errors": dict(self._errors),
            }

    def adoption(self) -> Dict[str, Any]:
        with self._lock:
            plugins_active = {
                pid: sum(counts.values())
                for pid, counts in self._per_plugin.items()
            }
            integrations_active = {
                integration: sum(counts.values())
                for integration, counts in self._per_integration.items()
            }
        return {
            "plugins": sorted(plugins_active.items(), key=lambda kv: -kv[1]),
            "integrations": sorted(integrations_active.items(), key=lambda kv: -kv[1]),
        }

    def health(self) -> Dict[str, Any]:
        """Roll up errors-per-event counts to surface integration/API health."""

        with self._lock:
            total_errors = sum(self._errors.values())
            total_events = sum(self._counters.values())
        error_rate = (total_errors / total_events) if total_events else 0.0
        status = "healthy"
        if error_rate > 0.1:
            status = "degraded"
        if error_rate > 0.25:
            status = "critical"
        return {
            "status": status,
            "error_rate": round(error_rate, 4),
            "events": total_events,
            "errors": total_errors,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {"name": e.name, "payload": e.payload, "timestamp": e.timestamp}
                for e in list(self._events)[-limit:]
            ]


_GLOBAL_MONITOR: Optional[EcosystemMonitor] = None


def get_ecosystem_monitor() -> EcosystemMonitor:
    global _GLOBAL_MONITOR
    if _GLOBAL_MONITOR is None:
        _GLOBAL_MONITOR = EcosystemMonitor()
    return _GLOBAL_MONITOR