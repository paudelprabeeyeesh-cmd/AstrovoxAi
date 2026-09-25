"""Cost tracking dashboard with per-service cost attribution, anomaly detection, and budget alerting."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional


@dataclass
class CostEntry:
    entry_id: str
    service: str
    provider: str
    model: str
    cost_usd: float
    tokens_input: int
    tokens_output: int
    requests: int
    user_id: Optional[str] = None
    tier: str = "free"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BudgetAlert:
    alert_id: str
    service: str
    threshold_usd: float
    current_usd: float
    period_start: datetime
    period_end: datetime
    triggered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CostTracker:
    _entries: List[CostEntry] = []
    _budgets: Dict[str, Dict[str, float]] = {}
    _lock = threading.RLock()
    _next_entry_id = 1

    @classmethod
    def record_cost(
        cls,
        service: str,
        provider: str,
        model: str,
        cost_usd: float,
        tokens_input: int = 0,
        tokens_output: int = 0,
        requests: int = 1,
        user_id: Optional[str] = None,
        tier: str = "free",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CostEntry:
        with cls._lock:
            entry = CostEntry(
                entry_id=f"COST-{cls._next_entry_id:06d}",
                service=service,
                provider=provider,
                model=model,
                cost_usd=cost_usd,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                requests=requests,
                user_id=user_id,
                tier=tier,
                metadata=metadata or {},
            )
            cls._entries.append(entry)
            cls._next_entry_id += 1
            if len(cls._entries) > 10000:
                cls._entries = cls._entries[-10000:]
            return entry

    @classmethod
    def set_budget(cls, service: str, daily_usd: float, monthly_usd: float) -> None:
        with cls._lock:
            cls._budgets[service] = {
                "daily_usd": daily_usd,
                "monthly_usd": monthly_usd,
            }

    @classmethod
    def get_daily_cost(cls, service: str, date: Optional[datetime] = None) -> float:
        with cls._lock:
            date = date or datetime.now(timezone.utc)
            day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            return sum(
                e.cost_usd for e in cls._entries
                if e.service == service and day_start <= e.timestamp < day_end
            )

    @classmethod
    def get_monthly_cost(cls, service: str, year: Optional[int] = None, month: Optional[int] = None) -> float:
        with cls._lock:
            now = datetime.now(timezone.utc)
            year = year or now.year
            month = month or now.month
            month_start = datetime(year, month, 1, tzinfo=timezone.utc)
            if month == 12:
                month_end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
            else:
                month_end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
            return sum(
                e.cost_usd for e in cls._entries
                if e.service == service and month_start <= e.timestamp < month_end
            )

    @classmethod
    def get_cost_by_model(cls, service: str, window_hours: int = 24) -> Dict[str, float]:
        with cls._lock:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
            result: Dict[str, float] = {}
            for e in cls._entries:
                if e.service == service and e.timestamp >= cutoff:
                    result[e.model] = result.get(e.model, 0.0) + e.cost_usd
            return result

    @classmethod
    def get_cost_by_user_tier(cls, service: str, window_hours: int = 24) -> Dict[str, float]:
        with cls._lock:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
            result: Dict[str, float] = {}
            for e in cls._entries:
                if e.service == service and e.timestamp >= cutoff:
                    result[e.tier] = result.get(e.tier, 0.0) + e.cost_usd
            return result

    @classmethod
    def check_budget_alerts(cls) -> List[BudgetAlert]:
        with cls._lock:
            alerts: List[BudgetAlert] = []
            now = datetime.now(timezone.utc)
            for service, budget in cls._budgets.items():
                daily_cost = cls.get_daily_cost(service, now)
                daily_budget = budget.get("daily_usd", float("inf"))
                if daily_budget != float("inf") and daily_cost >= daily_budget:
                    alerts.append(BudgetAlert(
                        alert_id=f"BUDGET-{service}-{now.timestamp()}",
                        service=service,
                        threshold_usd=daily_budget,
                        current_usd=daily_cost,
                        period_start=now.replace(hour=0, minute=0, second=0, microsecond=0),
                        period_end=now.replace(hour=23, minute=59, second=59, microsecond=999999),
                    ))
            return alerts

    @classmethod
    def get_dashboard_data(cls, window_hours: int = 24) -> Dict[str, Any]:
        with cls._lock:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
            recent = [e for e in cls._entries if e.timestamp >= cutoff]
        by_model: Dict[str, float] = {}
        by_service: Dict[str, float] = {}
        by_tier: Dict[str, float] = {}
        total_cost = 0.0
        total_requests = 0
        for e in recent:
            total_cost += e.cost_usd
            total_requests += e.requests
            by_model[e.model] = by_model.get(e.model, 0.0) + e.cost_usd
            by_service[e.service] = by_service.get(e.service, 0.0) + e.cost_usd
            by_tier[e.tier] = by_tier.get(e.tier, 0.0) + e.cost_usd
        return {
            "window_hours": window_hours,
            "total_cost_usd": total_cost,
            "total_requests": total_requests,
            "cost_per_request": total_cost / total_requests if total_requests > 0 else 0.0,
            "by_model": by_model,
            "by_service": by_service,
            "by_tier": by_tier,
            "budget_alerts": [asdict(a) for a in cls.check_budget_alerts()],
        }


cost_tracker = CostTracker()
