"""Operational Dashboard — cluster health, workflow status, plugin status, performance metrics, security alerts, audit history, compatibility warnings."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class HealthStatus:
    component: str
    status: str
    last_check: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowStatus:
    workflow_id: str
    execution_id: str
    status: str
    started_at: str = ""
    completed_at: str = ""
    step_count: int = 0
    error: Optional[str] = None


@dataclass
class PluginStatus:
    plugin_id: str
    name: str
    version: str
    state: str
    last_error: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceMetric:
    name: str
    value: float
    unit: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class SecurityAlert:
    alert_id: str
    severity: str
    title: str
    description: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    acknowledged: bool = False


@dataclass
class AuditEvent:
    event_id: str
    actor: str
    action: str
    target: str
    result: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CompatibilityWarning:
    entry_id: str
    message: str
    severity: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class OperationalDashboard:
    """Aggregates operational data for the ecosystem."""

    def __init__(self) -> None:
        self._health: Dict[str, HealthStatus] = {}
        self._workflows: Dict[str, WorkflowStatus] = {}
        self._plugins: Dict[str, PluginStatus] = {}
        self._metrics: List[PerformanceMetric] = []
        self._alerts: List[SecurityAlert] = []
        self._audit: List[AuditEvent] = []
        self._compatibility_warnings: List[CompatibilityWarning] = []
        self._lock = threading.Lock()

    def record_health(self, component: str, status: str, details: Optional[Dict[str, Any]] = None) -> None:
        with self._lock:
            self._health[component] = HealthStatus(component=component, status=status, details=details or {})

    def update_workflow(self, status: WorkflowStatus) -> None:
        with self._lock:
            self._workflows[status.execution_id] = status

    def update_plugin(self, status: PluginStatus) -> None:
        with self._lock:
            self._plugins[status.plugin_id] = status

    def add_metric(self, metric: PerformanceMetric) -> None:
        with self._lock:
            self._metrics.append(metric)

    def add_alert(self, alert: SecurityAlert) -> None:
        with self._lock:
            self._alerts.append(alert)

    def add_audit_event(self, event: AuditEvent) -> None:
        with self._lock:
            self._audit.append(event)

    def add_compatibility_warning(self, warning: CompatibilityWarning) -> None:
        with self._lock:
            self._compatibility_warnings.append(warning)

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "health": {k: v.__dict__ for k, v in self._health.items()},
                "workflows": [w.__dict__ for w in self._workflows.values()][-50:],
                "plugins": [p.__dict__ for p in self._plugins.values()][-50:],
                "metrics": [m.__dict__ for m in self._metrics][-200:],
                "security_alerts": [a.__dict__ for a in self._alerts][-100:],
                "audit_history": [e.__dict__ for e in self._audit][-200:],
                "compatibility_warnings": [w.__dict__ for w in self._compatibility_warnings][-100:],
            }

    def health_report(self) -> Dict[str, Any]:
        with self._lock:
            degraded = [c for c, h in self._health.items() if h.status != "healthy"]
            return {
                "total_components": len(self._health),
                "healthy_components": len(self._health) - len(degraded),
                "degraded_components": degraded,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }


_dashboard = OperationalDashboard()


def get_dashboard() -> OperationalDashboard:
    return _dashboard
