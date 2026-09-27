"""
Cost tracking for AstrovoxAI.
Tracks spending, generates alerts, and forecasts costs.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CostBreakdown:
    developer_id: str
    period_start: datetime
    period_end: datetime
    total_cost: float
    by_service: Dict[str, float] = field(default_factory=dict)
    by_model: Dict[str, float] = field(default_factory=dict)
    by_project: Dict[str, float] = field(default_factory=dict)
    daily_costs: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "developer_id": self.developer_id,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_cost": self.total_cost,
            "by_service": self.by_service,
            "by_model": self.by_model,
            "by_project": self.by_project,
            "daily_costs": self.daily_costs,
        }


@dataclass
class CostAlert:
    alert_id: str
    developer_id: str
    threshold: float
    current_spend: float
    alert_type: str
    message: str
    triggered_at: datetime = field(default_factory=datetime.utcnow)
    acknowledged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "developer_id": self.developer_id,
            "threshold": self.threshold,
            "current_spend": self.current_spend,
            "alert_type": self.alert_type,
            "message": self.message,
            "triggered_at": self.triggered_at.isoformat(),
            "acknowledged": self.acknowledged,
        }


class CostTracker:
    """Tracks costs and manages budget alerts."""

    def __init__(self):
        self._cost_records: List[Dict[str, Any]] = []
        self._alerts: Dict[str, CostAlert] = {}
        self._budgets: Dict[str, float] = {}

    def record_cost(
        self,
        developer_id: str,
        amount: float,
        service: str,
        model_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> None:
        record = {
            "developer_id": developer_id,
            "amount": amount,
            "service": service,
            "model_id": model_id,
            "project_id": project_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._cost_records.append(record)
        self._check_budget_alerts(developer_id)

    def get_cost_breakdown(
        self,
        developer_id: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> CostBreakdown:
        start = start or datetime.utcnow() - timedelta(days=30)
        end = end or datetime.utcnow()
        records = [
            r for r in self._cost_records
            if r["developer_id"] == developer_id
            and start <= datetime.fromisoformat(r["timestamp"]) <= end
        ]
        by_service: Dict[str, float] = {}
        by_model: Dict[str, float] = {}
        by_project: Dict[str, float] = {}
        daily_costs: Dict[str, float] = {}
        total_cost = 0.0
        for r in records:
            amount = r["amount"]
            total_cost += amount
            by_service[r["service"]] = by_service.get(r["service"], 0.0) + amount
            if r.get("model_id"):
                by_model[r["model_id"]] = by_model.get(r["model_id"], 0.0) + amount
            if r.get("project_id"):
                by_project[r["project_id"]] = by_project.get(r["project_id"], 0.0) + amount
            day = datetime.fromisoformat(r["timestamp"]).date().isoformat()
            daily_costs[day] = daily_costs.get(day, 0.0) + amount
        return CostBreakdown(
            developer_id=developer_id,
            period_start=start,
            period_end=end,
            total_cost=total_cost,
            by_service=by_service,
            by_model=by_model,
            by_project=by_project,
            daily_costs=daily_costs,
        )

    def set_budget(self, developer_id: str, monthly_budget: float) -> None:
        self._budgets[developer_id] = monthly_budget

    def get_budget(self, developer_id: str) -> Optional[float]:
        return self._budgets.get(developer_id)

    def _check_budget_alerts(self, developer_id: str) -> None:
        budget = self._budgets.get(developer_id)
        if not budget:
            return
        breakdown = self.get_cost_breakdown(developer_id)
        if breakdown.total_cost >= budget:
            alert = CostAlert(
                alert_id=str(uuid.uuid4()),
                developer_id=developer_id,
                threshold=budget,
                current_spend=breakdown.total_cost,
                alert_type="budget_exceeded",
                message=f"Monthly budget of ${budget:.2f} exceeded. Current spend: ${breakdown.total_cost:.2f}",
            )
            self._alerts[alert.alert_id] = alert
            logger.warning("Budget alert for %s: %s", developer_id, alert.message)

    def list_alerts(self, developer_id: str) -> List[CostAlert]:
        return [a for a in self._alerts.values() if a.developer_id == developer_id]
