"""Organization analytics — usage, engagement, and growth metrics."""

import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class OrgMetric:
    id: str
    org_id: str
    metric_type: str
    value: float
    dimensions: Dict[str, str] = field(default_factory=dict)
    recorded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class OrgAnalytics:
    def __init__(self):
        self._metrics: Dict[str, OrgMetric] = {}
        self._events: List[Dict[str, Any]] = []

    def track_event(self, org_id: str, event_name: str, user_id: str = "", properties: Optional[Dict[str, Any]] = None) -> None:
        event = {
            "event_id": str(uuid.uuid4()),
            "org_id": org_id,
            "event_name": event_name,
            "user_id": user_id,
            "properties": properties or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._events.append(event)
        logger.debug("Tracked event %s for org %s", event_name, org_id)

    def record_metric(self, org_id: str, metric_type: str, value: float, dimensions: Optional[Dict[str, str]] = None) -> OrgMetric:
        metric_id = str(uuid.uuid4())
        metric = OrgMetric(id=metric_id, org_id=org_id, metric_type=metric_type, value=value, dimensions=dimensions or {})
        self._metrics[metric_id] = metric
        logger.debug("Recorded metric %s=%s for org %s", metric_type, value, org_id)
        return metric

    def get_metrics(self, org_id: str, metric_type: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None) -> List[dict]:
        results = []
        for m in self._metrics.values():
            if m.org_id != org_id:
                continue
            if metric_type and m.metric_type != metric_type:
                continue
            if start and m.recorded_at < start:
                continue
            if end and m.recorded_at > end:
                continue
            results.append({
                "id": m.id,
                "metric_type": m.metric_type,
                "value": m.value,
                "dimensions": m.dimensions,
                "recorded_at": m.recorded_at,
            })
        return results

    def get_summary(self, org_id: str, metric_type: str) -> dict:
        values = [m.value for m in self._metrics.values() if m.org_id == org_id and m.metric_type == metric_type]
        if not values:
            return {"count": 0, "sum": 0.0, "avg": 0.0, "min": 0.0, "max": 0.0}
        return {
            "count": len(values),
            "sum": round(sum(values), 2),
            "avg": round(sum(values) / len(values), 2),
            "min": round(min(values), 2),
            "max": round(max(values), 2),
        }

    def get_engagement(self, org_id: str, days: int = 30) -> dict:
        cutoff = datetime.now(timezone.utc).isoformat()
        recent = [e for e in self._events if e["org_id"] == org_id and e["timestamp"] >= cutoff]
        unique_users = len({e["user_id"] for e in recent if e["user_id"]})
        event_counts = defaultdict(int)
        for e in recent:
            event_counts[e["event_name"]] += 1
        return {
            "period_days": days,
            "total_events": len(recent),
            "unique_users": unique_users,
            "top_events": dict(sorted(event_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
        }

    def export(self, org_id: str, fmt: str = "json") -> str:
        metrics = self.get_metrics(org_id)
        if fmt == "json":
            import json
            return json.dumps(metrics, indent=2)
        lines = ["metric_type,value,recorded_at"]
        for m in metrics:
            lines.append(f"{m['metric_type']},{m['value']},{m['recorded_at']}")
        return "\n".join(lines)


org_analytics = OrgAnalytics()
