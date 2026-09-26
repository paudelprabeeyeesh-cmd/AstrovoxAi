"""AI dashboard."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing: Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AIDashboardWidget:
    widget_id: str
    title: str
    metric: str
    chart_type: str
    options: Dict[str, Any] = field(default_factory=dict)


class AIDashboard:
    def __init__(self) -> None:
        self._dashboards: Dict[str, Dict[str, Any]] = {}

    def create(self, name: str, widgets: Optional[List[AIDashboardWidget]] = None) -> Dict[str, Any]:
        dashboard_id = uuid.uuid4().hex
        dashboard = {
            "dashboard_id": dashboard_id,
            "name": name,
            "widgets": [w.__dict__ for w in (widgets or [])],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._dashboards[dashboard_id] = dashboard
        return dashboard


ai_dashboard = AIDashboard()
