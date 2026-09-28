import logging
import re
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, List, Mapping, Optional, Pattern, Sequence, TypedDict

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


class HealthCheck(TypedDict, total=False):
    name: str
    status: HealthStatus
    message: str
    duration_ms: float
    checked_at: str
    metadata: Mapping[str, Any]


@dataclass
class HealthResult:
    checks: List[HealthCheck]
    overall_status: HealthStatus
    summary: str
    checked_at: str
    failures: List[HealthCheck] = field(default_factory=list)

    def to_dict(self) -> Mapping[str, Any]:
        return {
            "checks": self.checks,
            "overall_status": self.overall_status.value,
            "summary": self.summary,
            "checked_at": self.checked_at,
            "failures": self.failures,
        }


HealthChecker = Callable[[], HealthCheck]


class FailureDetector:
    def __init__(
        self,
        checkers: Sequence[HealthChecker],
        *,
        anomaly_window: int = 20,
        anomaly_threshold: float = 2.5,
    ) -> None:
        self.checkers = list(checkers)
        self.anomaly_window = anomaly_window
        self.anomaly_threshold = anomaly_threshold
        self._history: List[float] = []
        self._failure_counts: Mapping[str, int] = {}

    def register(self, checker: HealthChecker) -> None:
        self.checkers.append(checker)

    def check(self) -> HealthResult:
        checks: List[HealthCheck] = []
        checked_at = datetime.utcnow().isoformat(timespec="milliseconds")

        for checker in self.checkers:
            start = time.perf_counter()
            try:
                check = checker()
            except Exception as exc:
                check = HealthCheck(
                    name=checker.__name__,
                    status=HealthStatus.FAIL,
                    message=str(exc),
                    checked_at=checked_at,
                )
            duration = (time.perf_counter() - start) * 1000
            check.setdefault("duration_ms", duration)
            check.setdefault("checked_at", checked_at)
            checks.append(check)

        overall = HealthStatus.PASS
        failures: List[HealthCheck] = []
        for check in checks:
            if check["status"] == HealthStatus.FAIL:
                overall = HealthStatus.FAIL
                failures.append(check)
            elif overall == HealthStatus.PASS and check["status"] == HealthStatus.WARN:
                overall = HealthStatus.WARN

        self._failure_counts = {check["name"]: self._failure_counts.get(check["name"], 0) + 1 for check in failures}

        if failures:
            summary = f"{len(failures)} check(s) failed: " + ", ".join(check["name"] for check in failures)
        elif overall == HealthStatus.WARN:
            summary = f"{len([c for c in checks if c['status'] == HealthStatus.WARN])} warning(s)"
        else:
            summary = "all checks passed"

        return HealthResult(
            checks=checks,
            overall_status=overall,
            summary=summary,
            checked_at=checked_at,
            failures=failures,
        )

    def detect_anomalies(self, latency: float) -> float:
        self._history.append(latency)
        if len(self._history) > self.anomaly_window:
            self._history.pop(0)

        if len(self._history) < 5:
            return 0.0

        mean = sum(self._history) / len(self._history)
        variance = sum((x - mean) ** 2 for x in self._history) / len(self._history)
        std = variance ** 0.5
        if std == 0:
            return 0.0

        z_score = abs((latency - mean) / std)
        return z_score

    def generate_alert(
        self,
        result: HealthResult,
        *,
        channels: Sequence[str] = ("log",),
    ) -> Mapping[str, Any]:
        severity = "critical" if result.overall_status == HealthStatus.FAIL else "warning"
        alert = {
            "alert_id": f"alert-{int(time.time())}",
            "severity": severity,
            "summary": result.summary,
            "status": result.overall_status.value,
            "checked_at": result.checked_at,
            "checks": [
                {
                    "name": check["name"],
                    "status": check["status"].value,
                    "message": check.get("message", ""),
                }
                for check in result.checks
            ],
            "channels": list(channels),
        }
        if "log" in channels:
            for check in result.failures:
                logger.error("Health check failed: %s - %s", check["name"], check.get("message", ""))
        return alert
