"""FinOps automation for cost optimization and budget management."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CostCategory(str, Enum):
    COMPUTE = "compute"
    STORAGE = "storage"
    NETWORK = "network"
    DATABASE = "database"
    AI_INFERENCE = "ai_inference"
    THIRD_PARTY = "third_party"
    SUPPORT = "support"
    DEVELOPER_TOOLS = "developer_tools"


class OptimizationStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


class BudgetAlertThreshold(str, Enum):
    WARNING = "warning"
    CRITICAL = "critical"
    EXCEEDED = "exceeded"


@dataclass
class CostItem:
    item_id: str
    service: str
    category: CostCategory
    amount: float
    currency: str = "usd"
    date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Budget:
    budget_id: str
    name: str
    amount: float
    period: str
    alert_threshold: BudgetAlertThreshold = BudgetAlertThreshold.WARNING
    alert_ratio: float = 0.8
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CostOptimization:
    optimization_id: str
    title: str
    category: CostCategory
    resource_id: str
    current_monthly_cost: float
    projected_monthly_savings: float
    implementation_effort: str
    priority: str
    status: OptimizationStatus = OptimizationStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def roi_months(self) -> float:
        return self.current_monthly_cost / max(self.projected_monthly_savings, 0.01)

    @property
    def annual_savings(self) -> float:
        return self.projected_monthly_savings * 12


class FinOpsManager:
    """Manage FinOps automation and cost optimization."""

    def __init__(self) -> None:
        self._costs: List[CostItem] = []
        self._budgets: List[Budget] = []
        self._optimizations: List[CostOptimization] = []
        self._daily_reports: Dict[str, Dict[str, Any]] = {}
        self._anomalies: List[Dict[str, Any]] = []
        logger.info("FinOps manager initialized")

    def record_cost(self, item: CostItem) -> None:
        self._costs.append(item)
        logger.debug("Recorded cost: %s (%s)", item.service, item.amount)

    def add_budget(self, budget: Budget) -> None:
        self._budgets.append(budget)
        logger.info("Added budget: %s (%s)", budget.name, budget.amount)

    def add_optimization(self, opt: CostOptimization) -> None:
        self._optimizations.append(opt)
        logger.info("Added optimization: %s ($$%.2f/mo)", opt.title, opt.projected_monthly_savings)

    def get_monthly_cost(self, year: int, month: int) -> float:
        return sum(
            c.amount for c in self._costs
            if c.date.year == year and c.date.month == month
        )

    def get_cost_by_category(self, year: int, month: int) -> Dict[CostCategory, float]:
        from collections import defaultdict
        totals: Dict[CostCategory, float] = defaultdict(float)
        for c in self._costs:
            if c.date.year == year and c.date.month == month:
                totals[c.category] += c.amount
        return dict(totals)

    def get_cost_by_service(self, year: int, month: int) -> Dict[str, float]:
        from collections import defaultdict
        totals: Dict[str, float] = defaultdict(float)
        for c in self._costs:
            if c.date.year == year and c.date.month == month:
                totals[c.service] += c.amount
        return dict(totals)

    def get_budget_status(self, year: int, month: int) -> Dict[str, Any]:
        statuses = {}
        for b in self._budgets:
            spent = self.get_monthly_cost(year, month)
            if b.period == "yearly":
                if b.name.endswith(str(year)):
                    spent = sum(c.amount for c in self._costs if c.date.year == year)
            utilization = spent / b.amount if b.amount > 0 else 0.0
            statuses[b.name] = {
                "budget": b.amount,
                "spent": spent,
                "utilization": utilization,
                "remaining": b.amount - spent,
                "alert": b.alert_threshold.value if utilization >= b.alert_ratio else "ok",
            }
        return statuses

    def get_optimization_savings(self) -> Dict[str, float]:
        completed = [o for o in self._optimizations if o.status == OptimizationStatus.COMPLETED]
        return {
            "monthly": sum(o.projected_monthly_savings for o in completed),
            "annual": sum(o.annual_savings for o in completed),
            "total_optimizations": len(completed),
        }

    def detect_anomalies(self, year: int, month: int) -> List[Dict[str, Any]]:
        by_service = self.get_cost_by_service(year, month)
        if not by_service:
            return []
        avg = sum(by_service.values()) / len(by_service)
        std = (sum((v - avg) ** 2 for v in by_service.values()) / len(by_service)) ** 0.5
        anomalies = []
        for svc, cost in by_service.items():
            if std > 0 and (cost - avg) / std > 2.0:
                anomalies.append({
                    "service": svc,
                    "cost": cost,
                    "average": avg,
                    "std": std,
                    "z_score": (cost - avg) / std,
                    "severity": "high" if (cost - avg) / std > 3.0 else "medium",
                })
        return anomalies

    def generate_monthly_report(self, year: int, month: int) -> Dict[str, Any]:
        return {
            "period": f"{year}-{month:02d}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "monthly_cost": self.get_monthly_cost(year, month),
            "by_category": {k.value: v for k, v in self.get_cost_by_category(year, month).items()},
            "by_service": self.get_cost_by_service(year, month),
            "budget_status": self.get_budget_status(year, month),
            "optimizations": self.get_optimization_savings(),
            "anomalies": self.detect_anomalies(year, month),
        }

    def generate_optimization_recommendations(self) -> List[Dict[str, Any]]:
        recommendations = []
        for opt in self._optimizations:
            if opt.status == OptimizationStatus.PENDING:
                recommendations.append({
                    "optimization_id": opt.optimization_id,
                    "title": opt.title,
                    "category": opt.category.value,
                    "monthly_savings": opt.projected_monthly_savings,
                    "annual_savings": opt.annual_savings,
                    "roi_months": opt.roi_months,
                    "priority": opt.priority,
                })
        recommendations.sort(key=lambda r: r["monthly_savings"], reverse=True)
        return recommendations


_finops: Optional[FinOpsManager] = None


def get_finops_manager() -> FinOpsManager:
    global _finops
    if _finops is None:
        _finops = FinOpsManager()
    return _finops
