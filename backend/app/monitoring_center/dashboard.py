"""Monitoring dashboard and widgets."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MonitoringWidget:
    widget_id: str
    title: str
    metric: str
    chart_type: str
    options: Dict[str, Any] = field(default_factory=dict)


class MonitoringDashboard:
    def __init__(self) -> None:
        self._dashboards: Dict[str, Dict[str, Any]] = {}

    def create_dashboard(self, name: str, widgets: Optional[List[MonitoringWidget]] = None) -> Dict[str, Any]:
        dashboard_id = uuid.uuid4().hex
        dashboard = {
            "dashboard_id": dashboard_id,
            "name": name,
            "widgets": [w.__dict__ for w in (widgets or [])],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._dashboards[dashboard_id] = dashboard
        return dashboard

    def get_dashboard(self, dashboard_id: str) -> Optional[Dict[str, Any]]:
        return self._dashboards.get(dashboard_id)


monitoring_dashboard = MonitoringDashboard()
