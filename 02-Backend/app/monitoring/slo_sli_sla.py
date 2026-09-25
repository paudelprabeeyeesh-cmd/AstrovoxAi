"""SLO/SLI/SLA management."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class SLIType(Enum):
    LATENCY = "latency"
    AVAILABILITY = "availability"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"
    DURABILITY = "durability"


@dataclass
class SLI:
    name: str
    sli_type: SLIType
    target: float
    window_days: int = 30
    current_value: float = 0.0
    description: str = ""


@dataclass
class SLO:
    name: str
    slis: List[SLI]
    description: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SLA:
    name: str
    slo: SLO
    credits: Dict[str, float] = field(default_factory=dict)
    penalty_terms: str = ""


class SLIManager:
    _slis: Dict[str, SLI] = {}

    @classmethod
    def register_sli(cls, sli: SLI) -> None:
        cls._slis[sli.name] = sli

    @classmethod
    def update_sli(cls, name: str, value: float) -> None:
        sli = cls._slis.get(name)
        if sli:
            sli.current_value = value

    @classmethod
    def check_compliance(cls, name: str) -> tuple[bool, float]:
        sli = cls._slis.get(name)
        if not sli:
            return False, 0.0
        return sli.current_value >= sli.target, sli.current_value / sli.target if sli.target > 0 else 0.0
