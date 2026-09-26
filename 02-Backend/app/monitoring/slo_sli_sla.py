"""SLO/SLI/SLA management with monitoring dashboards."""

from typing import Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class SLIType(Enum):
    LATENCY = "latency"
    AVAILABILITY = "availability"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"
    DURABILITY = "durability"


class DashboardPanel(Enum):
    LINE_CHART = "line_chart"
    GAUGE = "gauge"
    BAR_CHART = "bar_chart"
    TABLE = "table"


@dataclass
class SLI:
    name: str
    sli_type: SLIType
    target: float
    window_days: int = 30
    current_value: float = 0.0
    description: str = ""
    history: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class SLO:
    name: str
    slis: List[SLI]
    description: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    dashboard_panels: List[str] = field(default_factory=list)


@dataclass
class SLA:
    name: str
    slo: SLO
    credits: Dict[str, float] = field(default_factory=dict)
    penalty_terms: str = ""
    status: str = "active"


class SLIManager:
    _slis: Dict[str, SLI] = {}
    _slos: Dict[str, SLO] = {}
    _slas: Dict[str, SLA] = {}

    @classmethod
    def register_sli(cls, sli: SLI) -> None:
        cls._slis[sli.name] = sli

    @classmethod
    def update_sli(cls, name: str, value: float) -> None:
        sli = cls._slis.get(name)
        if not sli:
            return
        sli.current_value = value
        sli.history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "value": value
        })
        if len(sli.history) > 1000:
            sli.history = sli.history[-1000:]

    @classmethod
    def check_compliance(cls, name: str) -> tuple[bool, float]:
        sli = cls._slis.get(name)
        if not sli:
            return False, 0.0
        return sli.current_value >= sli.target, sli.current_value / sli.target if sli.target > 0 else 0.0

    @classmethod
    def register_slo(cls, slo: SLO) -> None:
        cls._slos[slo.name] = slo

    @classmethod
    def register_sla(cls, sla: SLA) -> None:
        cls._slas[sla.name] = sla

    @classmethod
    def get_slo_health(cls, name: str) -> Dict[str, Any]:
        slo = cls._slos.get(name)
        if not slo:
            return {}
        sli_health = {}
        for sli in slo.slis:
            compliant, ratio = cls.check_compliance(sli.name)
            sli_health[sli.name] = {
                "type": sli.sli_type.value,
                "current": sli.current_value,
                "target": sli.target,
                "compliant": compliant,
                "ratio": ratio
            }
        return {
            "name": name,
            "slis": sli_health,
            "overall_compliant": all(v["compliant"] for v in sli_health.values()),
            "created_at": slo.created_at.isoformat()
        }

    @classmethod
    def get_dashboard_data(cls, name: str) -> Dict[str, Any]:
        slo = cls._slos.get(name)
        if not slo:
            return {}
        panels = []
        for sli in slo.slis:
            compliant, ratio = cls.check_compliance(sli.name)
            panels.append({
                "panel_type": DashboardPanel.GAUGE.value,
                "title": f"{sli.name} ({sli.sli_type.value})",
                "current_value": sli.current_value,
                "target": sli.target,
                "unit": "%",
                "status": "healthy" if compliant else "critical",
                "history": sli.history[-50:]
            })
        return {
            "dashboard_name": name,
            "panels": panels,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

    @classmethod
    def get_sla_compliance(cls, name: str) -> Dict[str, Any]:
        sla = cls._slas.get(name)
        if not sla:
            return {}
        slo_health = cls.get_slo_health(sla.slo.name)
        return {
            "sla_name": name,
            "status": sla.status,
            "credits": sla.credits,
            "penalty_terms": sla.penalty_terms,
            "slo_health": slo_health
        }

    @classmethod
    def list_all_slis(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": sli.name,
                "type": sli.sli_type.value,
                "target": sli.target,
                "current": sli.current_value,
                "compliant": cls.check_compliance(sli.name)[0]
            }
            for sli in cls._slis.values()
        ]

    @classmethod
    def list_all_slos(cls) -> List[str]:
        return list(cls._slos.keys())

    @classmethod
    def list_all_slas(cls) -> List[str]:
        return list(cls._slas.keys())

