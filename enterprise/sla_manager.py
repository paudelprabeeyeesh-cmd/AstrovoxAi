"""
SLA management for AstrovoxAI.
Defines, monitors, and enforces service level agreements.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SLAStatus(str, Enum):
    MET = "met"
    AT_RISK = "at_risk"
    BREACHED = "breached"


@dataclass
class SLAConfig:
    sla_id: str
    name: str
    availability_target: float
    latency_p99_target_ms: float
    resolution_time_target_hours: int
    credits_enabled: bool = True
    credit_percentage: int = 10

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sla_id": self.sla_id,
            "name": self.name,
            "availability_target": self.availability_target,
            "latency_p99_target_ms": self.latency_p99_target_ms,
            "resolution_time_target_hours": self.resolution_time_target_hours,
            "credits_enabled": self.credits_enabled,
            "credit_percentage": self.credit_percentage,
        }


@dataclass
class SLAStatusRecord:
    sla_id: str
    period_start: datetime
    period_end: datetime
    status: SLAStatus
    availability: float
    actual_latency_p99_ms: float
    breaches: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sla_id": self.sla_id,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "status": self.status.value,
            "availability": self.availability,
            "actual_latency_p99_ms": self.actual_latency_p99_ms,
            "breaches": self.breaches,
        }


class SLAManager:
    """Manages SLAs, monitors compliance, and issues credits."""

    def __init__(self):
        self._slas: Dict[str, SLAConfig] = {}
        self._status_records: List[SLAStatusRecord] = []
        self._initialize_defaults()

    def _initialize_defaults(self) -> None:
        self._slas["standard"] = SLAConfig(
            sla_id="standard",
            name="Standard",
            availability_target=0.99,
            latency_p99_target_ms=500,
            resolution_time_target_hours=24,
            credit_percentage=10,
        )
        self._slas["enterprise"] = SLAConfig(
            sla_id="enterprise",
            name="Enterprise",
            availability_target=0.999,
            latency_p99_target_ms=200,
            resolution_time_target_hours=4,
            credit_percentage=25,
        )

    def register_sla(self, config: SLAConfig) -> None:
        self._slas[config.sla_id] = config
        logger.info("Registered SLA %s", config.sla_id)

    def get_sla(self, sla_id: str) -> Optional[SLAConfig]:
        return self._slas.get(sla_id)

    def list_slas(self) -> List[SLAConfig]:
        return list(self._slas.values())

    def evaluate_sla(
        self,
        sla_id: str,
        period_start: datetime,
        period_end: datetime,
        availability: float,
        latency_p99_ms: float,
    ) -> SLAStatusRecord:
        sla = self._slas.get(sla_id)
        if not sla:
            raise ValueError(f"SLA {sla_id} not found")
        breaches = []
        if availability < sla.availability_target:
            breaches.append({"metric": "availability", "expected": sla.availability_target, "actual": availability})
        if latency_p99_ms > sla.latency_p99_target_ms:
            breaches.append({"metric": "latency_p99", "expected": sla.latency_p99_target_ms, "actual": latency_p99_ms})
        status = SLAStatus.BREACHED if breaches else SLAStatus.MET
        if availability >= sla.availability_target * 0.99 and not breaches:
            status = SLAStatus.MET
        elif availability < sla.availability_target and not breaches:
            status = SLAStatus.AT_RISK
        record = SLAStatusRecord(
            sla_id=sla_id,
            period_start=period_start,
            period_end=period_end,
            status=status,
            availability=availability,
            actual_latency_p99_ms=latency_p99_ms,
            breaches=breaches,
        )
        self._status_records.append(record)
        return record
