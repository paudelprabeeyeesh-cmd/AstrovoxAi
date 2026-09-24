"""Workflow automation engine."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class WorkflowStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowStep:
    step_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    tool_name: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    timeout_seconds: float = 30.0
    retries: int = 0


@dataclass
class Workflow:
    workflow_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    steps: List[WorkflowStep] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.DRAFT
    user_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkflowAutomation:
    """Workflow automation engine with dependency resolution."""

    def __init__(self, tool_registry):
        self._tool_registry = tool_registry
        self._workflows: Dict[str, Workflow] = {}
        self._running: Dict[str, bool] = {}

    def create_workflow(self, name: str, steps: List[Dict[str, Any]], user_id: Optional[str] = None) -> Workflow:
        workflow = Workflow(name=name, steps=[WorkflowStep(**s) for s in steps], user_id=user_id)
        self._workflows[workflow.workflow_id] = workflow
        logger.info("Created workflow %s with %d steps", name, len(steps))
        return workflow

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        return self._workflows.get(workflow_id)

    def list_workflows(self, user_id: Optional[str] = None) -> List[Workflow]:
        return [wf for wf in self._workflows.values() if user_id is None or wf.user_id == user_id]

    def execute(self, workflow_id: str, use_cache: bool = True) -> Workflow:
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        workflow.status = WorkflowStatus.RUNNING
        self._running[workflow_id] = True
        results: Dict[str, Any] = {}
        try:
            self._execute_steps(workflow, results, use_cache=use_cache)
            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = time.time()
        except Exception as exc:  # noqa: BLE001
            logger.error("Workflow %s failed: %s", workflow_id, exc)
            workflow.status = WorkflowStatus.FAILED
            workflow.metadata["error"] = str(exc)
        finally:
            self._running[workflow_id] = False
        return workflow

    def _execute_steps(self, workflow: Workflow, results: Dict[str, Any], use_cache: bool = True) -> None:
        for step in workflow.steps:
            if not self._running.get(workflow.workflow_id, False):
                workflow.status = WorkflowStatus.CANCELLED
                return
            if not all(dep in results for dep in step.depends_on):
                continue
            resolved_args = self._resolve_args(step.arguments, results)
            execution = self._tool_registry.execute(
                tool_name=step.tool_name,
                arguments=resolved_args,
                user_id=workflow.user_id,
                use_cache=use_cache,
            )
            if execution.error:
                raise RuntimeError(f"Step {step.name} failed: {execution.error}")
            results[step.step_id] = execution.result

    def _resolve_args(self, args: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        resolved = {}
        for key, value in args.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                ref = value[2:-1]
                resolved[key] = results.get(ref)
            else:
                resolved[key] = value
        return resolved

    def cancel(self, workflow_id: str) -> bool:
        self._running[workflow_id] = False
        workflow = self._workflows.get(workflow_id)
        if workflow:
            workflow.status = WorkflowStatus.CANCELLED
            return True
        return False


from app.tool_registry import tool_registry

workflow_automation = WorkflowAutomation(tool_registry=tool_registry)
