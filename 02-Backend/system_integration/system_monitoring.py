"""
System health monitoring.

Collects health metrics, runs health checks, and raises alerts.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Dict, List, Optional


class HealthState(Enum):
    OK = auto()
    WARNING = auto()
    CRITICAL = auto()


@dataclass
class HealthCheck:
    name: str
    check: Callable[[], bool]
    interval: float = 10.0
    threshold: int = 3
    last_status: HealthState = HealthState.OK
    consecutive_failures: int = 0


@dataclass
class Metric:
    name: str
    value: float
    timestamp: float = 0.0
    tags: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    def __init__(self) -> None:
        self._metrics: Dict[str, List[Metric]] = {}
        self._lock = threading.RLock()
        self._counters: Dict[str, float] = {}

    def record(self, metric: Metric) -> None:
        with self._lock:
            self._metrics.setdefault(metric.name, []).append(metric)

    def increment(self, name: str, amount: float = 1.0, tags: Optional[Dict[str, str]] = None) -> None:
        with self._lock:
            self._counters[name] = self._counters.get(name, 0.0) + amount
            self.record(Metric(name=name, value=self._counters[name], timestamp=time.time(), tags=tags or {}))

    def snapshot(self) -> Dict[str, Metric]:
        snap = {}
        with self._lock:
            for name, metrics in self._metrics.items():
                if metrics:
                    snap[name] = metrics[-1]
        return snap

    def history(self, name: str, limit: int = 100) -> List[Metric]:
        with self._lock:
            return list(self._metrics.get(name, []))[-limit:]


class SystemMonitor:
    def __init__(self) -> None:
        self._checks: List[HealthCheck] = []
        self._alerts: List[Callable[[str, str], None]] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._status: Dict[str, HealthState] = {}
        self.metrics = MetricsCollector()

    def register_check(self, check: HealthCheck) -> None:
        self._checks.append(check)
        self._status[check.name] = check.last_status

    def add_alert(self, handler: Callable[[str, str], None]) -> None:
        self._alerts.append(handler)

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while self._running:
            self._tick()
            time.sleep(1.0)

    def _tick(self) -> None:
        for check in self._checks:
            now = time.time()
            ok = False
            try:
                ok = check.check()
            except Exception as _e:  # noqa: BLE001
                ok = False
            if ok:
                check.consecutive_failures = 0
                check.last_status = HealthState.OK
            else:
                check.consecutive_failures += 1
                if check.consecutive_failures >= check.threshold:
                    check.last_status = HealthState.CRITICAL
                    for handler in self._alerts:
                        try:
                            handler(check.name, "CRITICAL")
                        except Exception as _e:  # noqa: BLE001
                            continue
                else:
                    check.last_status = HealthState.WARNING
            self._status[check.name] = check.last_status
            self.metrics.record(Metric(name="health", value=check.consecutive_failures, timestamp=now))

    def status(self) -> Dict[str, HealthState]:
        return dict(self._status)

    def overall(self) -> HealthState:
        states = list(self._status.values())
        if not states:
            return HealthState.OK
        if all(s == HealthState.OK for s in states):
            return HealthState.OK
        if any(s == HealthState.CRITICAL for s in states):
            return HealthState.CRITICAL
        return HealthState.WARNING

    def stop(self) -> None:
        self._running = False
