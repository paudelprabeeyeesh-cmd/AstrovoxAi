"""Dashboard framework for business intelligence."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DashboardWidget:
    widget_id: str
    title: str
    chart_type: str
    data_source: str
    config: Dict[str, Any] = field(default_factory=dict)


class Dashboard:
    def __init__(self) -> None:
        self._dashboards: Dict[str, Any] = {}

    def create(self, name: str, owner: str, widgets: Optional[List[DashboardWidget]] = None) -> Dict[str, Any]:
        dashboard_id = uuid.uuid4().hex
        dashboard = {
            "dashboard_id": dashboard_id,
            "name": name,
            "owner": owner,
            "widgets": [w.__dict__ for w in (widgets or [])],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._dashboards[dashboard_id] = dashboard
        return dashboard

    def get(self, dashboard_id: str) -> Optional[Dict[str, Any]]:
        return self._dashboards.get(dashboard_id)


dashboard = Dashboard()
