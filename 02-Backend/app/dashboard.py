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
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum

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
        from .multi_agent import agent_orchestrator
        from .workflow_engine import workflow_engine

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
        from .multi_agent import agent_orchestrator
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
        from .workflow_engine import workflow_engine
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
