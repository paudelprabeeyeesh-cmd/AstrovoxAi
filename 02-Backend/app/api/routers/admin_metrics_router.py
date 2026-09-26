"""Admin metrics and reporting endpoints."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/metrics", tags=["admin-metrics"])


class MetricsSummary(BaseModel):
    timestamp: str
    uptime_seconds: float
    requests_total: int
    requests_by_status: Dict[str, int]
    requests_by_endpoint: Dict[str, int]
    avg_duration_ms: float
    p99_duration_ms: float
    errors_total: int


class MetricsQueryResponse(BaseModel):
    data: List[Dict[str, Any]]
    count: int


class HealthDependency(BaseModel):
    name: str
    status: str
    latency_ms: Optional[float] = None
    error: Optional[str] = None


class HealthAggregateResponse(BaseModel):
    status: str
    dependencies: List[HealthDependency]
    timestamp: str


class EnterpriseMetricsSummary(BaseModel):
    timestamp: str
    total_tenants: int
    active_tenants: int
    total_organizations: int
    total_users: int
    total_workspaces: int
    total_support_tickets: int
    open_tickets: int
    total_partners: int
    total_audit_exports: int
    total_billing_records: int
    total_quota_violations: int


_metrics_store: List[Dict[str, Any]] = []
_start_time = time.time()


def record_metric(data: Dict[str, Any]) -> None:
    _metrics_store.append(data)
    if len(_metrics_store) > 100_000:
        _metrics_store[:] = _metrics_store[-50_000:]


@router.get("/summary", response_model=MetricsSummary)
async def get_metrics_summary():
    durations = [m.get("duration_ms", 0) for m in _metrics_store if "duration_ms" in m]
    status_counts: Dict[str, int] = defaultdict(int)
    endpoint_counts: Dict[str, int] = defaultdict(int)
    errors = 0
    for m in _metrics_store:
        status_counts[str(m.get("status", "unknown"))] += 1
        endpoint_counts[m.get("path", "unknown")] += 1
        if m.get("status", 0) >= 500:
            errors += 1

    sorted_durations = sorted(durations)
    p99 = sorted_durations[int(len(sorted_durations) * 0.99)] if sorted_durations else 0.0
    avg = sum(durations) / len(durations) if durations else 0.0

    return MetricsSummary(
        timestamp=datetime.now(timezone.utc).isoformat(),
        uptime_seconds=round(time.time() - _start_time, 2),
        requests_total=len(_metrics_store),
        requests_by_status=dict(status_counts),
        requests_by_endpoint=dict(endpoint_counts),
        avg_duration_ms=round(avg, 2),
        p99_duration_ms=round(p99, 2),
        errors_total=errors,
    )


@router.get("/query", response_model=MetricsQueryResponse)
async def query_metrics(
    path: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
):
    data = list(_metrics_store)
    if path:
        data = [m for m in data if m.get("path") == path]
    if status:
        data = [m for m in data if str(m.get("status")) == str(status)]
    data.sort(key=lambda m: m.get("timestamp", ""), reverse=True)
    return MetricsQueryResponse(data=data[:limit], count=len(data))


@router.get("/health", response_model=HealthAggregateResponse)
async def aggregate_health():
    deps: List[Dict[str, Any]] = []
    db_ok, db_err = _check_database()
    deps.append({"name": "database", "status": "healthy" if db_ok else "degraded", "error": db_err})
    deps.append({"name": "filesystem", "status": "healthy", "error": None})
    deps.append({"name": "memory", "status": "healthy", "error": None})

    status = "healthy" if all(d["status"] == "healthy" for d in deps) else "degraded"
    return HealthAggregateResponse(
        status=status,
        dependencies=[HealthDependency(**d) for d in deps],
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/enterprise", response_model=EnterpriseMetricsSummary)
async def get_enterprise_metrics():
    try:
        from app.multi_tenancy import tenant_manager
        from app.repositories.database.client import get_db
        from app.support import support_ticket_service
        from app.partners import partner_service

        with get_db() as conn:
            total_users = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
            total_orgs = conn.execute("SELECT COUNT(*) as c FROM organizations").fetchone()["c"]
            total_workspaces = conn.execute("SELECT COUNT(*) as c FROM workspaces").fetchone()["c"]

        open_tickets = len([t for t in support_ticket_service.list_tickets() if t.status == "open"])
        total_tickets = len(support_ticket_service.list_tickets())
        total_partners = len(partner_service.list_partners())

        return EnterpriseMetricsSummary(
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_tenants=len(tenant_manager.tenants),
            active_tenants=len([t for t in tenant_manager.tenants.values() if t.is_active]),
            total_organizations=total_orgs,
            total_users=total_users,
            total_workspaces=total_workspaces,
            total_support_tickets=total_tickets,
            open_tickets=open_tickets,
            total_partners=total_partners,
            total_audit_exports=0,
            total_billing_records=0,
            total_quota_violations=0,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


def _check_database() -> tuple[bool, Optional[str]]:
    try:
        from app.database.database import get_db
        with get_db() as conn:
            conn.execute("SELECT 1")
        return True, None
    except Exception as exc:
        return False, str(exc)
