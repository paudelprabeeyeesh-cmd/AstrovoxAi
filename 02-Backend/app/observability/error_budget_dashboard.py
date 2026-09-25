"""Error budget dashboard with burn rate alerts, SLI tracking, and compliance visualization."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional


@dataclass
class ErrorBudgetSnapshot:
    slo_name: str
    target_slo: float
    window_days: int
    error_budget_total: float
    error_budget_remaining: float
    error_budget_consumed_pct: float
    burn_rate_per_hour: float
    projected_exhaustion_days: Optional[float]
    compliance_pct: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    alerts: List[Dict[str, Any]] = field(default_factory=list)


class ErrorBudgetDashboard:
    _snapshots: Dict[str, List[ErrorBudgetSnapshot]] = {}
    _lock = threading.RLock()
    _max_history = 1000

    @classmethod
    def record_snapshot(cls, snapshot: ErrorBudgetSnapshot) -> None:
        with cls._lock:
            cls._snapshots.setdefault(snapshot.slo_name, []).append(snapshot)
            history = cls._snapshots[snapshot.slo_name]
            if len(history) > cls._max_history:
                cls._snapshots[snapshot.slo_name] = history[-cls._max_history:]

    @classmethod
    def get_snapshot(cls, slo_name: str, limit: int = 100) -> List[ErrorBudgetSnapshot]:
        with cls._lock:
            return list(cls._snapshots.get(slo_name, [])[-limit:])

    @classmethod
    def get_current_budget(cls, slo_name: str) -> Optional[Dict[str, Any]]:
        snapshots = cls.get_snapshot(slo_name, limit=1)
        if not snapshots:
            return None
        s = snapshots[-1]
        return {
            "slo_name": s.slo_name,
            "target_slo": s.target_slo,
            "window_days": s.window_days,
            "error_budget_total": s.error_budget_total,
            "error_budget_remaining": s.error_budget_remaining,
            "error_budget_consumed_pct": s.error_budget_consumed_pct,
            "burn_rate_per_hour": s.burn_rate_per_hour,
            "projected_exhaustion_days": s.projected_exhaustion_days,
            "compliance_pct": s.compliance_pct,
            "status": cls._derive_status(s),
            "timestamp": s.timestamp.isoformat(),
        }

    @classmethod
    def get_dashboard_summary(cls) -> Dict[str, Any]:
        with cls._lock:
            summary: Dict[str, Any] = {
                "slos": [],
                "alerts_count": 0,
                "exhausted_budgets": [],
                "healthy_budgets": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            for slo_name, history in cls._snapshots.items():
                if not history:
                    continue
                current = history[-1]
                status = cls._derive_status(current)
                summary["slos"].append({
                    "slo_name": slo_name,
                    "status": status,
                    "remaining_pct": (current.error_budget_remaining / current.error_budget_total) * 100
                    if current.error_budget_total > 0 else 0,
                    "burn_rate": current.burn_rate_per_hour,
                })
                summary["alerts_count"] += len(current.alerts)
                if "exhausted" in status:
                    summary["exhausted_budgets"].append(slo_name)
                elif status == "healthy":
                    summary["healthy_budgets"].append(slo_name)
            return summary

    @classmethod
    def get_trend_data(cls, slo_name: str, window_hours: int = 24) -> Dict[str, Any]:
        snapshots = cls.get_snapshot(slo_name)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
        points = [
            {
                "timestamp": s.timestamp.isoformat(),
                "remaining_pct": (s.error_budget_remaining / s.error_budget_total) * 100
                if s.error_budget_total > 0 else 0,
                "burn_rate": s.burn_rate_per_hour,
                "compliance_pct": s.compliance_pct,
            }
            for s in snapshots
            if s.timestamp >= cutoff
        ]
        return {
            "slo_name": slo_name,
            "points": points,
            "window_hours": window_hours,
        }

    @classmethod
    def _derive_status(cls, snapshot: ErrorBudgetSnapshot) -> str:
        if snapshot.error_budget_remaining <= 0:
            return "exhausted"
        remaining_pct = (snapshot.error_budget_remaining / snapshot.error_budget_total) * 100 if snapshot.error_budget_total > 0 else 0
        if remaining_pct <= 10:
            return "critical"
        if remaining_pct <= 25:
            return "warning"
        if snapshot.compliance_pct >= snapshot.target_slo * 100:
            return "healthy"
        return "at_risk"

    @classmethod
    def generate_grafana_panel(cls) -> Dict[str, Any]:
        return {
            "title": "Error Budget Remaining",
            "type": "gauge",
            "targets": [
                {
                    "expr": "error_budget_remaining_pct",
                    "legendFormat": "{{slo_name}}",
                }
            ],
            "fieldConfig": {
                "defaults": {
                    "unit": "percent",
                    "min": 0,
                    "max": 100,
                    "thresholds": {
                        "steps": [
                            {"value": 0, "color": "red"},
                            {"value": 25, "color": "orange"},
                            {"value": 50, "color": "yellow"},
                            {"value": 75, "color": "green"},
                        ]
                    },
                }
            },
        }


error_budget_dashboard = ErrorBudgetDashboard()
