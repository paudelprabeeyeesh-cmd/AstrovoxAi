"""Dashboard template pack with reusable Grafana, Prometheus, and frontend dashboard definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class PanelDef:
    title: str
    type: str
    targets: List[Dict[str, Any]] = field(default_factory=list)
    gridPos: Optional[Dict[str, int]] = None
    description: str = ""


@dataclass
class DashboardTemplate:
    template_id: str
    name: str
    description: str
    tags: List[str] = field(default_factory=list)
    panels: List[PanelDef] = field(default_factory=list)
    time_range: str = "last 6 hours"
    refresh: str = "30s"
    schema_version: int = 38
    version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def _overview_dashboard() -> DashboardTemplate:
    panels = [
        PanelDef(
            title="Request Rate",
            type="graph",
            targets=[{"expr": "sum(rate(http_requests_total[5m]))", "legendFormat": "{{method}} {{endpoint}}"}],
            gridPos={"x": 0, "y": 0, "w": 12, "h": 8},
            description="HTTP request rate per second",
        ),
        PanelDef(
            title="Error Rate",
            type="graph",
            targets=[{"expr": "sum(rate(http_requests_total{status=~\"5..\"}[5m])) / sum(rate(http_requests_total[5m])) * 100", "legendFormat": "error_rate_pct"}],
            gridPos={"x": 12, "y": 0, "w": 12, "h": 8},
            description="5xx error rate percentage",
        ),
        PanelDef(
            title="P95 Latency",
            type="graph",
            targets=[{"expr": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, endpoint))", "legendFormat": "{{endpoint}}"}],
            gridPos={"x": 0, "y": 8, "w": 12, "h": 8},
            description="P95 request latency in seconds",
        ),
        PanelDef(
            title="Active Alerts",
            type="stat",
            targets=[{"expr": "count(up == 0)", "legendFormat": "down"}],
            gridPos={"x": 12, "y": 8, "w": 6, "h": 4},
            description="Number of currently firing alerts",
        ),
        PanelDef(
            title="Active Users",
            type="stat",
            targets=[{"expr": "active_users", "legendFormat": "active"}],
            gridPos={"x": 18, "y": 8, "w": 6, "h": 4},
            description="Number of active users in the last 5 minutes",
        ),
    ]
    return DashboardTemplate(
        template_id="overview",
        name="AstrovoxAI Overview",
        description="System-wide overview dashboard",
        tags=["default", "overview", "production"],
        panels=panels,
    )


def _sli_dashboard() -> DashboardTemplate:
    panels = [
        PanelDef(
            title="Availability SLI",
            type="gauge",
            targets=[{"expr": "avg_over_time((sum(http_requests_total{status!~\"5..\"}) / sum(http_requests_total))[30d:1m]) * 100", "legendFormat": "availability_pct"}],
            gridPos={"x": 0, "y": 0, "w": 6, "h": 6},
            description="Service availability percentage over 30 days",
        ),
        PanelDef(
            title="Latency SLI",
            type="gauge",
            targets=[{"expr": "avg_over_time((histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le)) < 2)[30d:1m]) * 100", "legendFormat": "latency_sli_pct"}],
            gridPos={"x": 6, "y": 0, "w": 6, "h": 6},
            description="Latency SLI percentage over 30 days",
        ),
        PanelDef(
            title="Error Budget Remaining",
            type="gauge",
            targets=[{"expr": "error_budget_remaining * 100", "legendFormat": "error_budget_pct"}],
            gridPos={"x": 12, "y": 0, "w": 6, "h": 6},
            description="Error budget remaining percentage",
        ),
        PanelDef(
            title="SLO Compliance History",
            type="graph",
            targets=[{"expr": "slo_compliance_ratio", "legendFormat": "compliance"}],
            gridPos={"x": 0, "y": 6, "w": 18, "h": 8},
            description="SLO compliance ratio over time",
        ),
    ]
    return DashboardTemplate(
        template_id="sli_tracker",
        name="SLO/SLI Tracker",
        description="Track SLOs and SLIs with error budgets",
        tags=["slo", "sli", "error_budget", "production"],
        panels=panels,
        time_range="last 30 days",
        refresh="5m",
    )


def _ai_metrics_dashboard() -> DashboardTemplate:
    panels = [
        PanelDef(
            title="AI Requests by Model",
            type="graph",
            targets=[{"expr": "sum(rate(ai_requests_total[5m])) by (model)", "legendFormat": "{{model}}"}],
            gridPos={"x": 0, "y": 0, "w": 12, "h": 8},
        ),
        PanelDef(
            title="Token Consumption",
            type="graph",
            targets=[{"expr": "sum(rate(ai_tokens_total[5m])) by (model)", "legendFormat": "{{model}}"}],
            gridPos={"x": 12, "y": 0, "w": 12, "h": 8},
        ),
        PanelDef(
            title="AI Error Rate",
            type="graph",
            targets=[{"expr": "sum(rate(ai_requests_total{status=\"error\"}[5m])) / sum(rate(ai_requests_total[5m])) * 100", "legendFormat": "error_rate_pct"}],
            gridPos={"x": 0, "y": 8, "w": 12, "h": 8},
        ),
        PanelDef(
            title="Cache Performance",
            type="graph",
            targets=[
                {"expr": "sum(rate(cache_hits_total[5m])) by (backend_type)", "legendFormat": "{{backend_type}} hits"},
                {"expr": "sum(rate(cache_misses_total[5m])) by (backend_type)", "legendFormat": "{{backend_type}} misses"},
            ],
            gridPos={"x": 12, "y": 8, "w": 12, "h": 8},
        ),
    ]
    return DashboardTemplate(
        template_id="ai_metrics",
        name="AI Metrics",
        description="AI service metrics including requests, tokens, and cache performance",
        tags=["ai", "metrics", "production"],
        panels=panels,
    )


def _cost_dashboard() -> DashboardTemplate:
    panels = [
        PanelDef(
            title="Daily AI Cost",
            type="graph",
            targets=[{"expr": "sum(increase(ai_cost_usd_total[24h])) by (model)", "legendFormat": "{{model}}"}],
            gridPos={"x": 0, "y": 0, "w": 12, "h": 8},
        ),
        PanelDef(
            title="Cost per Request",
            type="stat",
            targets=[{"expr": "sum(ai_cost_usd_total) / sum(ai_requests_total)", "legendFormat": "cost_per_req"}],
            gridPos={"x": 12, "y": 0, "w": 6, "h": 4},
        ),
        PanelDef(
            title="Monthly Projection",
            type="stat",
            targets=[{"expr": "sum(increase(ai_cost_usd_total[1h])) * 24 * 30", "legendFormat": "monthly_proj"}],
            gridPos={"x": 18, "y": 0, "w": 6, "h": 4},
        ),
        PanelDef(
            title="Cost by User Tier",
            type="pie",
            targets=[{"expr": "sum(ai_cost_usd_total) by (user_tier)", "legendFormat": "{{user_tier}}"}],
            gridPos={"x": 0, "y": 8, "w": 12, "h": 8},
        ),
    ]
    return DashboardTemplate(
        template_id="cost_tracking",
        name="Cost Tracking",
        description="AI usage cost tracking and projections",
        tags=["cost", "billing", "production"],
        panels=panels,
        time_range="last 7 days",
        refresh="1m",
    )


def _incident_dashboard() -> DashboardTemplate:
    panels = [
        PanelDef(
            title="Active Incidents",
            type="table",
            targets=[{"expr": "active_incidents", "legendFormat": "incidents"}],
            gridPos={"x": 0, "y": 0, "w": 24, "h": 8},
            description="Currently active incidents",
        ),
        PanelDef(
            title="MTTR Trend",
            type="graph",
            targets=[{"expr": "avg_over_time(incident_mttr_seconds[7d])", "legendFormat": "mttr_7d"}],
            gridPos={"x": 0, "y": 8, "w": 12, "h": 8},
        ),
        PanelDef(
            title="Incident Frequency",
            type="graph",
            targets=[{"expr": "sum(increase(incidents_total[1d]))", "legendFormat": "incidents_per_day"}],
            gridPos={"x": 12, "y": 8, "w": 12, "h": 8},
        ),
    ]
    return DashboardTemplate(
        template_id="incidents",
        name="Incident Timeline",
        description="Incident timeline and MTTR tracking",
        tags=["incidents", "oncall", "production"],
        panels=panels,
        time_range="last 30 days",
        refresh="1m",
    )


class DashboardTemplatePack:
    _templates: Dict[str, DashboardTemplate] = {}

    @classmethod
    def register(cls, template: DashboardTemplate) -> None:
        cls._templates[template.template_id] = template

    @classmethod
    def get(cls, template_id: str) -> Optional[DashboardTemplate]:
        return cls._templates.get(template_id)

    @classmethod
    def list_all(cls) -> List[DashboardTemplate]:
        return list(cls._templates.values())

    @classmethod
    def export_grafana(cls, template_id: str) -> Dict[str, Any]:
        template = cls.get(template_id)
        if not template:
            return {}
        dashboard: Dict[str, Any] = {
            "dashboard": {
                "title": template.name,
                "description": template.description,
                "tags": template.tags,
                "timezone": "browser",
                "schemaVersion": template.schema_version,
                "version": template.version,
                "refresh": template.refresh,
                "time": {"from": f"now-{template.time_range.replace('last ', '')}", "to": "now"},
                "panels": [],
            },
            "overwrite": True,
        }
        y = 0
        for panel in template.panels:
            gp = panel.gridPos or {"x": 0, "y": y, "w": 12, "h": 8}
            y = gp["y"] + gp["h"]
            dashboard["dashboard"]["panels"].append({
                "title": panel.title,
                "type": panel.type,
                "gridPos": gp,
                "targets": panel.targets,
                "description": panel.description,
            })
        return dashboard

    @classmethod
    def export_prometheus_rules(cls) -> List[Dict[str, Any]]:
        return [
            {
                "record": "request_rate",
                "expr": "sum(rate(http_requests_total[5m])) by (method, endpoint)",
            },
            {
                "record": "error_rate",
                "expr": "sum(rate(http_requests_total{status=~\"5..\"}[5m])) / sum(rate(http_requests_total[5m]))",
            },
            {
                "record": "p95_latency",
                "expr": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, endpoint))",
            },
            {
                "record": "slo_compliance_ratio",
                "expr": "avg_over_time((sum(http_requests_total{status!~\"5..\"}) / sum(http_requests_total))[30d:1m])",
            },
        ]


DashboardTemplatePack.register(_overview_dashboard())
DashboardTemplatePack.register(_sli_dashboard())
DashboardTemplatePack.register(_ai_metrics_dashboard())
DashboardTemplatePack.register(_cost_dashboard())
DashboardTemplatePack.register(_incident_dashboard())
