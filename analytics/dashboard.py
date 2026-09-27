"""
Analytics dashboard for AstrovoxAI.
Provides configurable dashboards with widgets for monitoring key metrics.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class WidgetType(str, Enum):
    METRIC = "metric"
    LINE_CHART = "line_chart"
    BAR_CHART = "bar_chart"
    TABLE = "table"
    GAUGE = "gauge"


@dataclass
class DashboardWidget:
    widget_id: str
    title: str
    widget_type: WidgetType
    query: str
    refresh_interval_seconds: int = 60
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "widget_id": self.widget_id,
            "title": self.title,
            "widget_type": self.widget_type.value,
            "query": self.query,
            "refresh_interval_seconds": self.refresh_interval_seconds,
            "config": self.config,
        }


class AnalyticsDashboard:
    """Manages analytics dashboards and widgets."""

    def __init__(self):
        self._dashboards: Dict[str, Dict[str, Any]] = {}
        self._widgets: Dict[str, DashboardWidget] = {}

    def create_dashboard(
        self,
        name: str,
        owner_id: str,
        description: str = "",
        is_public: bool = False,
    ) -> Dict[str, Any]:
        dashboard_id = str(uuid.uuid4())
        dashboard = {
            "dashboard_id": dashboard_id,
            "name": name,
            "owner_id": owner_id,
            "description": description,
            "is_public": is_public,
            "widgets": [],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        self._dashboards[dashboard_id] = dashboard
        logger.info("Created dashboard %s", dashboard_id)
        return dashboard

    def add_widget(
        self,
        dashboard_id: str,
        title: str,
        widget_type: WidgetType,
        query: str,
        refresh_interval_seconds: int = 60,
        config: Optional[Dict[str, Any]] = None,
    ) -> DashboardWidget:
        widget = DashboardWidget(
            widget_id=str(uuid.uuid4()),
            title=title,
            widget_type=widget_type,
            query=query,
            refresh_interval_seconds=refresh_interval_seconds,
            config=config or {},
        )
        self._widgets[widget.widget_id] = widget
        if dashboard_id in self._dashboards:
            self._dashboards[dashboard_id]["widgets"].append(widget.widget_id)
            self._dashboards[dashboard_id]["updated_at"] = datetime.utcnow().isoformat()
        logger.info("Added widget %s to dashboard %s", widget.widget_id, dashboard_id)
        return widget

    def get_dashboard(self, dashboard_id: str) -> Optional[Dict[str, Any]]:
        dashboard = self._dashboards.get(dashboard_id)
        if not dashboard:
            return None
        widgets = [self._widgets[w].to_dict() for w in dashboard.get("widgets", [])]
        return {**dashboard, "widgets": widgets}

    def list_dashboards(self, owner_id: Optional[str] = None) -> List[Dict[str, Any]]:
        dashboards = list(self._dashboards.values())
        if owner_id:
            dashboards = [d for d in dashboards if d["owner_id"] == owner_id]
        return dashboards

    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        logger.debug("Executing analytics query: %s", query)
        return [{"timestamp": datetime.utcnow().isoformat(), "value": 0}]
