"""Cost analysis templates and forecasting models."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum

from .cost_management import cost_tracker

logger = logging.getLogger(__name__)


class CostPeriod(str, Enum):
    """Cost analysis periods."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"


@dataclass
class CostTemplate:
    """Template for cost analysis."""
    name: str
    description: str
    period: CostPeriod
    model_filter: Optional[List[str]] = None
    provider_filter: Optional[List[str]] = None
    alert_thresholds: Dict[str, float] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


COST_ANALYSIS_TEMPLATES: Dict[str, CostTemplate] = {
    "default": CostTemplate(
        name="default",
        description="Default cost analysis across all models and providers",
        period=CostPeriod.MONTHLY,
        alert_thresholds={
            "daily_cost": 10.0,
            "monthly_cost": 100.0,
            "cost_per_request": 0.5,
        },
        tags=["default", "monitoring"],
    ),
    "enterprise": CostTemplate(
        name="enterprise",
        description="Enterprise cost analysis with higher thresholds",
        period=CostPeriod.MONTHLY,
        alert_thresholds={
            "daily_cost": 100.0,
            "monthly_cost": 1000.0,
            "cost_per_request": 5.0,
        },
        tags=["enterprise", "budget"],
    ),
    "startup": CostTemplate(
        name="startup",
        description="Startup cost analysis with strict limits",
        period=CostPeriod.WEEKLY,
        alert_thresholds={
            "daily_cost": 5.0,
            "weekly_cost": 20.0,
            "cost_per_request": 0.1,
        },
        tags=["startup", "budget"],
    ),
    "research": CostTemplate(
        name="research",
        description="Research lab cost analysis",
        period=CostPeriod.MONTHLY,
        model_filter=["gpt-4", "claude-3-opus", "gemini-pro"],
        alert_thresholds={
            "monthly_cost": 500.0,
            "cost_per_request": 2.0,
        },
        tags=["research", "experiments"],
    ),
    "embedding": CostTemplate(
        name="embedding",
        description="Embedding-specific cost analysis",
        period=CostPeriod.DAILY,
        model_filter=["text-embedding-ada-002", "embed-english-v3.0"],
        alert_thresholds={
            "daily_cost": 5.0,
            "cost_per_request": 0.001,
        },
        tags=["embeddings", "monitoring"],
    ),
}


class CostAnalysisEngine:
    """Analyze costs using templates."""

    def __init__(self) -> None:
        self._history: List[Dict[str, Any]] = []

    def analyze(self, template_name: str, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Run cost analysis using a template."""
        template = COST_ANALYSIS_TEMPLATES.get(template_name)
        if template is None:
            raise ValueError(f"Unknown template: {template_name}")

        report = cost_tracker.get_usage_report(user_id, days=days)
        forecast = cost_tracker.get_cost_forecast(user_id, days=30)

        period_multiplier = {
            CostPeriod.DAILY: 1,
            CostPeriod.WEEKLY: 7,
            CostPeriod.MONTHLY: 30,
            CostPeriod.QUARTERLY: 90,
            CostPeriod.ANNUALLY: 365,
        }[template.period]

        threshold_key = f"{template.period.value}_cost"
        alerts = []
        if threshold_key in template.alert_thresholds:
            period_cost_key = f"total_cost"
            period_cost = report.get(period_cost_key, 0)
            threshold = template.alert_thresholds[threshold_key]
            if period_cost > threshold:
                alerts.append({
                    "type": "budget_exceeded",
                    "threshold": threshold,
                    "actual": period_cost,
                    "period": template.period.value,
                })

        analysis = {
            "template": template_name,
            "period": template.period.value,
            "days": days,
            "report": report,
            "forecast": forecast,
            "alerts": alerts,
            "thresholds": template.alert_thresholds,
            "tags": template.tags,
            "timestamp": time.time(),
        }
        self._history.append(analysis)
        return analysis

    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get analysis history."""
        return self._history[-limit:]

    def list_templates(self) -> List[Dict[str, Any]]:
        """List available templates."""
        return [
            {
                "name": name,
                "description": tpl.description,
                "period": tpl.period.value,
                "alert_thresholds": tpl.alert_thresholds,
                "tags": tpl.tags,
            }
            for name, tpl in COST_ANALYSIS_TEMPLATES.items()
        ]


cost_analysis_engine = CostAnalysisEngine()
