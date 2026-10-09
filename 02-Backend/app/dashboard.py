<<<<<<< HEAD
"""User Interface API Layer.

Provides backend APIs for:
- Agent dashboard
- Running task list
- Workflow monitor
- Progress indicators
- Agent logs
- Execution timeline
- Task cancellation
- Workflow history
"""

import time
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ============================================================================
# Dashboard Models
# ============================================================================

@dataclass
class DashboardStats:
    """Overall platform statistics."""
    total_agents: int = 0
    active_agents: int = 0
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    running_workflows: int = 0
    total_users: int = 0
    uptime_seconds: float = 0.0


@dataclass
class TaskView:
    """View of a running task."""
    id: str
    name: str
    agent: str
    status: str
    progress: float = 0.0
    started_at: float = 0.0
    estimated_completion: float = 0.0
    result: str = ""


@dataclass
class WorkflowView:
    """View of a workflow execution."""
    id: str
    name: str
    status: str
    progress: float = 0.0
    current_step: str = ""
    total_steps: int = 0
    completed_steps: int = 0
    started_at: float = 0.0


@dataclass
class LogEntry:
    """A log entry."""
    timestamp: float
    level: str
    source: str
    message: str


@dataclass
class TimelineEvent:
    """An execution timeline event."""
    timestamp: str
    event_type: str
    description: str
    source: str
    details: dict = field(default_factory=dict)


# ============================================================================
# Dashboard Service
# ============================================================================

class DashboardService:
    """Service for dashboard data."""

    def __init__(self):
        self._logs: list[LogEntry] = []
        self._events: list[TimelineEvent] = []

    def get_stats(self) -> DashboardStats:
        """Get overall platform statistics."""
        from ...multi_agent import agent_orchestrator
        from ...workflow_engine import workflow_engine

        analytics = agent_orchestrator.get_analytics()
        wf_analytics = workflow_engine.get_analytics()

        total_tasks = 0
        agents = analytics.get("agents", [])
        if isinstance(agents, list):
            for a in agents:
                if isinstance(a, dict):
                    total_tasks += a.get("total_tasks", 0)

        return DashboardStats(
            total_agents=analytics.get("total_agents", 0),
            active_agents=analytics.get("total_agents", 0),
            total_tasks=total_tasks,
            completed_tasks=analytics.get("completed_plans", 0),
            failed_tasks=0,
            running_workflows=wf_analytics.get("running", 0),
            uptime_seconds=time.time(),
        )

    def get_running_tasks(self) -> list[TaskView]:
        """Get list of currently running tasks."""
        from ...multi_agent import agent_orchestrator
        tasks = []

        sessions = agent_orchestrator._sessions.values() if hasattr(agent_orchestrator, '_sessions') else []
        for session in sessions:
            for task in session.tasks:
                if task.status == TaskStatus.IN_PROGRESS:
                    tasks.append(TaskView(
                        id=task.id,
                        name=task.description[:50],
                        agent=task.agent_role if hasattr(task, 'agent_role') else task.role.value,
                        status=task.status.value if hasattr(task.status, 'value') else str(task.status),
                        progress=0.5,
                        started_at=time.time(),
                    ))
        return tasks

    def get_workflow_status(self) -> list[WorkflowView]:
        """Get status of workflow executions."""
        from ...workflow_engine import workflow_engine
        views = []
        for execution in workflow_engine._executions.values():
            wf = workflow_engine.get_workflow(execution.workflow_id)
            total = len(wf.steps) if wf else 0
            completed = len(execution.step_results)
            progress = (completed / max(total, 1)) * 100
            views.append(WorkflowView(
                id=execution.id,
                name=wf.name if wf else "Unknown",
                status=execution.status.value,
                progress=progress,
                current_step="",
                total_steps=total,
                completed_steps=completed,
                started_at=execution.started_at,
            ))
        return views

    def get_agent_logs(self, limit: int = 50) -> list[LogEntry]:
        """Get recent agent logs."""
        return self._logs[-limit:]

    def get_timeline(self, limit: int = 100) -> list[TimelineEvent]:
        """Get execution timeline."""
        return self._events[-limit:]

    def add_log(self, level: str, source: str, message: str):
        """Add a log entry."""
        self._logs.append(LogEntry(
            timestamp=time.time(),
            level=level,
            source=source,
            message=message,
        ))
        if len(self._logs) > 10000:
            self._logs = self._logs[-5000:]

    def add_event(self, event_type: str, description: str, source: str, details: dict = None):
        """Add a timeline event."""
        self._events.append(TimelineEvent(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
            event_type=event_type,
            description=description,
            source=source,
            details=details or {},
        ))
        if len(self._events) > 10000:
            self._events = self._events[-5000:]


dashboard_service = DashboardService()
=======
"""Monitoring dashboard configuration and helpers for AstrovoxAI backend.

Provides:
- DASHBOARD_PANELS: panel definitions consumable by Grafana or custom UIs.
- get_dashboard(): returns the full dashboard payload including metrics queries
  and health summary.
- metrics_summary(): lightweight current-state snapshot from Prometheus counters.
"""

import time
from typing import Any, Dict, List

from app.health import health_service
from app.metrics import PROMETHEUS_AVAILABLE, get_metrics

DASHBOARD_PANELS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "title": "Request Rate",
        "type": "graph",
        "targets": [
            {
                "expr": "sum(rate(http_requests_total[1m])) by (endpoint)",
                "legendFormat": "{{endpoint}}",
            }
        ],
        "unit": "rps",
    },
    {
        "id": 2,
        "title": "P95 Latency",
        "type": "graph",
        "targets": [
            {
                "expr": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, endpoint))",
                "legendFormat": "{{endpoint}}",
            }
        ],
        "unit": "s",
        "alert": {
            "name": "SlowResponses",
            "condition": "avg > 2s over 10m",
            "severity": "warning",
        },
    },
    {
        "id": 3,
        "title": "Error Rate (5xx)",
        "type": "graph",
        "targets": [
            {
                "expr": "sum(rate(http_errors_total[5m])) / sum(rate(http_requests_total[5m]))",
                "legendFormat": "5xx error rate",
            }
        ],
        "unit": "percentunit",
    },
    {
        "id": 4,
        "title": "Active Users",
        "type": "graph",
        "targets": [
            {"expr": "active_users", "legendFormat": "active users"}
        ],
    },
    {
        "id": 5,
        "title": "AI Requests by Model",
        "type": "graph",
        "targets": [
            {
                "expr": "sum(rate(ai_requests_total[5m])) by (model, status)",
                "legendFormat": "{{model}} - {{status}}",
            }
        ],
    },
    {
        "id": 6,
        "title": "Cache Hit Ratio",
        "type": "graph",
        "targets": [
            {
                "expr": "sum(rate(cache_hits_total[5m])) / (sum(rate(cache_hits_total[5m])) + sum(rate(cache_misses_total[5m])))",
                "legendFormat": "cache hit ratio",
            }
        ],
        "unit": "percentunit",
    },
    {
        "id": 7,
        "title": "Database Query P95",
        "type": "graph",
        "targets": [
            {
                "expr": "histogram_quantile(0.95, sum(rate(db_query_duration_seconds_bucket[5m])) by (le, operation))",
                "legendFormat": "{{operation}}",
            }
        ],
        "unit": "s",
    },
    {
        "id": 8,
        "title": "Memory Usage",
        "type": "graph",
        "targets": [
            {
                "expr": "process_resident_memory_bytes{job=\"astravox-backend\"}",
                "legendFormat": "resident memory",
            }
        ],
        "unit": "bytes",
    },
    {
        "id": 9,
        "title": "AI Request P95 Latency",
        "type": "graph",
        "targets": [
            {
                "expr": "histogram_quantile(0.95, sum(rate(ai_request_duration_seconds_bucket[5m])) by (le, model))",
                "legendFormat": "{{model}}",
            }
        ],
        "unit": "s",
    },
    {
        "id": 10,
        "title": "WebSocket Connections",
        "type": "graph",
        "targets": [
            {
                "expr": "sum(rate(websocket_connections_total[1m])) by (event)",
                "legendFormat": "{{event}}",
            }
        ],
        "unit": "rps",
    },
]


def get_dashboard(app=None) -> Dict[str, Any]:
    """Return the full dashboard payload."""
    health_service.app = app
    health = health_service.get_overall_health()
    raw_metrics = get_metrics() if PROMETHEUS_AVAILABLE else b""
    return {
        "dashboard": {
            "title": "AstrovoxAI Backend",
            "uid": "astrovox-backend",
            "timezone": "browser",
            "schemaVersion": 38,
            "version": 2,
            "refresh": "10s",
            "panels": DASHBOARD_PANELS,
        },
        "health": health,
        "metrics_available": PROMETHEUS_AVAILABLE,
        "metrics_raw": raw_metrics.decode("utf-8", errors="replace") if raw_metrics else "",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def metrics_summary() -> Dict[str, Any]:
    """Lightweight snapshot of key metric values (best-effort)."""
    if not PROMETHEUS_AVAILABLE:
        return {"prometheus_available": False}
    try:
        from prometheus_client import REGISTRY
        samples = {}
        for metric in REGISTRY.collect():
            for sample in metric.samples:
                key = sample.name
                if sample.labels:
                    key += ":" + ",".join(f"{k}={v}" for k, v in sample.labels.items())
                samples[key] = sample.value
        return {"prometheus_available": True, "samples": samples}
    except Exception as _e:  # noqa: BLE001
        return {"prometheus_available": True, "error": str(_e)}
>>>>>>> 10617909505295e4a37b817bb54db2364934b978
