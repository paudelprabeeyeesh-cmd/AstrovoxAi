"""SLA tracking and reporting."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class SLA:
    name: str
    target_availability: float
    max_error_budget_minutes: float
    response_time_slo_p95: float
    response_time_slo_p99: float


class SLATracker:
    def __init__(self) -> None:
        self._slas: Dict[str, SLA] = {
            "api": SLA(
                name="API",
                target_availability=0.99,
                max_error_budget_minutes=43.2,
                response_time_slo_p95=500.0,
                response_time_slo_p99=1500.0,
            ),
        }
        self._violations: List[Dict[str, str]] = []

    def record_violation(self, sla_name: str, reason: str) -> None:
        self._violations.append(
            {
                "sla": sla_name,
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def status(self) -> Dict[str, Dict[str, object]]:
        result: Dict[str, Dict[str, object]] = {}
        for name, sla in self._slas.items():
            sla_violations = [v for v in self._violations if v["sla"] == name]
            result[name] = {
                "target_availability": sla.target_availability,
                "violations": len(sla_violations),
                "recent_violation": sla_violations[-1] if sla_violations else None,
            }
        return result
