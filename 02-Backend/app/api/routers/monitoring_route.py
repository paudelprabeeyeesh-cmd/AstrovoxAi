"""Enhanced monitoring API routes exposing all observability endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List

from app.observability import (
    get_observability,
    DashboardTemplatePack,
    IncidentTimelineVisualizer,
    oncall,
    cost_tracker,
    usage_analytics,
    error_budget_dashboard,
    log_retention,
    sampler,
    HealthStatus,
)

router = APIRouter(prefix="/observability", tags=["observability"])


@router.get("/health")
async def health():
    obs = get_observability()
    overall = obs.health.get_overall_status()
    status_code = 200 if overall != HealthStatus.UNHEALTHY else 503
    return {"status": overall.value}


@router.get("/health/detailed")
async def detailed_health():
    obs = get_observability()
    return obs.get_status()


@router.get("/health/ready")
async def readiness():
    obs = get_observability()
    if obs.health.get_overall_status() == HealthStatus.UNHEALTHY:
        raise HTTPException(status_code=503, detail="Service not ready")
    return {"status": "ready"}


@router.get("/health/live")
async def liveness():
    return {"status": "alive"}


@router.get("/metrics")
async def metrics():
    obs = get_observability()
    return {"prometheus": obs.get_metrics_prometheus()}


@router.get("/alerts")
async def alerts():
    obs = get_observability()
    active = obs.alerts.get_active_alerts()
    return {
        "active_alerts": [
            {
                "rule_name": a.rule_name,
                "severity": a.severity.value,
                "status": a.status,
                "labels": a.labels,
                "annotations": a.annotations,
                "starts_at": a.starts_at,
                "ends_at": a.ends_at,
            }
            for a in active
        ],
        "count": len(active),
    }


@router.get("/alerts/history")
async def alert_history(limit: int = Query(100, ge=1, le=1000)):
    obs = get_observability()
    history = obs.alerts.get_alert_history(limit=limit)
    return {
        "alerts": [
            {
                "rule_name": a.rule_name,
                "severity": a.severity.value,
                "status": a.status,
                "starts_at": a.starts_at,
                "ends_at": a.ends_at,
            }
            for a in history
        ]
    }


@router.get("/dashboards/templates")
async def list_dashboard_templates():
    templates = DashboardTemplatePack.list_all()
    return {
        "templates": [
            {
                "template_id": t.template_id,
                "name": t.name,
                "description": t.description,
                "tags": t.tags,
                "panel_count": len(t.panels),
            }
            for t in templates
        ]
    }


@router.get("/dashboards/templates/{template_id}/grafana")
async def get_grafana_dashboard(template_id: str):
    data = DashboardTemplatePack.export_grafana(template_id)
    if not data:
        raise HTTPException(status_code=404, detail="Template not found")
    return data


@router.get("/dashboards/templates/{template_id}/panels")
async def get_dashboard_panels(template_id: str):
    template = DashboardTemplatePack.get(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return {
        "template_id": template.template_id,
        "name": template.name,
        "panels": [
            {
                "title": p.title,
                "type": p.type,
                "description": p.description,
                "gridPos": p.gridPos,
                "targets": p.targets,
            }
            for p in template.panels
        ],
    }


@router.get("/incidents")
async def list_incidents(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
):
    from app.observability.incident_timeline import IncidentStatus, IncidentSeverity
    st = IncidentStatus(status) if status else None
    sv = IncidentSeverity(severity) if severity else None
    incidents = IncidentTimelineVisualizer.list_incidents(status=st, severity=sv, limit=limit)
    return {
        "incidents": [
            {
                "incident_id": i.incident_id,
                "title": i.title,
                "severity": i.severity.value,
                "status": i.status.value,
                "owner": i.owner,
                "created_at": i.created_at.isoformat(),
                "resolved_at": i.resolved_at.isoformat() if i.resolved_at else None,
                "affected_services": i.affected_services,
            }
            for i in incidents
        ]
    }


@router.get("/incidents/{incident_id}")
async def get_incident(incident_id: str):
    incident = IncidentTimelineVisualizer.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return IncidentTimelineVisualizer.export_timeline(incident_id)


@router.get("/incidents/{incident_id}/timeline")
async def get_incident_timeline(incident_id: str):
    events = IncidentTimelineVisualizer.get_timeline_events(incident_id)
    return {
        "incident_id": incident_id,
        "events": [
            {
                "event_id": e.event_id,
                "phase": e.phase.value,
                "timestamp": e.timestamp.isoformat(),
                "actor": e.actor,
                "action": e.action,
                "details": e.details,
                "duration_ms": e.duration_ms,
            }
            for e in events
        ],
    }


@router.get("/incidents/mttr")
async def get_mttr():
    return IncidentTimelineVisualizer.get_mttr()


@router.post("/incidents")
async def create_incident(
    title: str,
    severity: str,
    description: str = "",
    affected_services: Optional[List[str]] = None,
    owner: str = "",
):
    from app.observability.incident_timeline import IncidentSeverity
    try:
        sv = IncidentSeverity(severity)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid severity")
    incident = IncidentTimelineVisualizer.create_incident(
        title=title,
        severity=sv,
        description=description,
        affected_services=affected_services or [],
        owner=owner,
    )
    return {
        "incident_id": incident.incident_id,
        "title": incident.title,
        "severity": incident.severity.value,
        "status": incident.status.value,
    }


@router.post("/incidents/{incident_id}/resolve")
async def resolve_incident(incident_id: str, root_cause: str = ""):
    incident = IncidentTimelineVisualizer.resolve_incident(incident_id, root_cause=root_cause)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {
        "incident_id": incident.incident_id,
        "status": incident.status.value,
        "root_cause": incident.root_cause,
    }


@router.get("/oncall/policy")
async def get_oncall_policy():
    return oncall.get_policy_summary()


@router.get("/oncall/escalations")
async def get_pending_escalations():
    pending = oncall.get_pending_escalations()
    return {
        "pending_escalations": [
            {
                "event_id": e.event_id,
                "incident_id": e.incident_id,
                "escalation_level": e.escalation_level.value,
                "action": e.action.value,
                "target_person_id": e.target_person_id,
                "response_deadline": e.response_deadline.isoformat() if e.response_deadline else None,
            }
            for e in pending
        ]
    }


@router.get("/cost/dashboard")
async def cost_dashboard(window_hours: int = Query(24, ge=1, le=720)):
    return cost_tracker.get_dashboard_data(window_hours=window_hours)


@router.get("/cost/budgets")
async def cost_budgets():
    return {"budgets": cost_tracker._budgets}


@router.get("/analytics/usage")
async def usage_dashboard(window_hours: int = Query(24, ge=1, le=720)):
    return usage_analytics.get_dashboard_data(window_hours=window_hours)


@router.get("/analytics/features")
async def feature_adoption(window_days: int = Query(30, ge=1, le=365)):
    return usage_analytics.get_feature_adoption(window_days=window_days)


@router.get("/analytics/top-features")
async def top_features(limit: int = Query(10, ge=1, le=100)):
    return usage_analytics.get_top_features(limit=limit)


@router.get("/error-budget/summary")
async def error_budget_summary():
    return error_budget_dashboard.get_dashboard_summary()


@router.get("/error-budget/{slo_name}")
async def error_budget_detail(slo_name: str):
    data = error_budget_dashboard.get_current_budget(slo_name)
    if not data:
        raise HTTPException(status_code=404, detail="SLO not found")
    return data


@router.get("/error-budget/{slo_name}/trend")
async def error_budget_trend(slo_name: str, window_hours: int = Query(24, ge=1, le=720)):
    return error_budget_dashboard.get_trend_data(slo_name, window_hours=window_hours)


@router.get("/sampling/stats")
async def sampling_stats():
    return sampler.get_stats()


@router.post("/sampling/strategy")
async def set_sampling_strategy(strategy: str, probability: float = Query(0.1, ge=0.0, le=1.0)):
    try:
        from app.observability.trace_sampling import SamplingStrategy
        s = SamplingStrategy(strategy)
        sampler.set_strategy(s, probability=probability)
        return {"status": "ok", "strategy": s.value, "probability": probability}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid strategy")


@router.get("/retention/stats")
async def retention_stats():
    return log_retention.get_stats().__dict__


@router.post("/retention/run")
async def run_retention_cleanup(dry_run: bool = Query(False)):
    log_retention.set_dry_run(dry_run)
    stats = log_retention.run_cleanup()
    return {"status": "ok", "dry_run": dry_run, "stats": stats.__dict__}
