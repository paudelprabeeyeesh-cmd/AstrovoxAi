"""Governance dashboard for compliance and policy visibility."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class GovernanceMetric:
    metric_id: str
    name: str
    value: Any
    unit: str
    category: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: Dict[str, str] = field(default_factory=dict)


class GovernanceDashboard:
    def __init__(self) -> None:
        self._metrics: Dict[str, List[GovernanceMetric]] = {}
        self._policies: Dict[str, Any] = {}

    def record_metric(self, metric: GovernanceMetric) -> None:
        self._metrics.setdefault(metric.category, []).append(metric)
        logger.debug("Recorded metric %s: %s %s", metric.metric_id, metric.value, metric.unit)

    def get_metrics(self, category: str, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        metrics = self._metrics.get(category, [])
        if since:
            metrics = [m for m in metrics if m.timestamp >= since]
        return [
            {
                "metric_id": m.metric_id,
                "name": m.name,
                "value": m.value,
                "unit": m.unit,
                "timestamp": m.timestamp.isoformat(),
                "tags": m.tags,
            }
            for m in metrics
        ]

    def get_compliance_summary(self) -> Dict[str, Any]:
        total = sum(len(ms) for ms in self._metrics.values())
        return {
            "total_metrics": total,
            "categories": list(self._metrics.keys()),
            "policy_count": len(self._policies),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def add_policy(self, policy_id: str, policy_data: Dict[str, Any]) -> None:
        self._policies[policy_id] = policy_data

    def get_policy(self, policy_id: str) -> Optional[Dict[str, Any]]:
        return self._policies.get(policy_id)


governance_dashboard = GovernanceDashboard()
