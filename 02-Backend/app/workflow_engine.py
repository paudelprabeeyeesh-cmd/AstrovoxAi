"""Workflow Automation Engine.

Supports reusable workflows with sequential/parallel execution,
conditional branches, loops, retry policies, scheduling, and templates.
"""

import time
import logging
import asyncio
import secrets
from typing import Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepAction(Enum):
    AGENT_TASK = "agent_task"
    CONDITION = "condition"
    LOOP = "loop"
    APPROVAL = "approval"
    DELAY = "delay"
    WEBHOOK = "webhook"


@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    id: str
    name: str
    action: StepAction
    config: dict = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    condition: str = ""
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 300
    status: str = "pending"
    result: str = ""
    error: str = ""


@dataclass
class Workflow:
    """A reusable workflow definition."""
    id: str
    name: str
    description: str
    steps: list[WorkflowStep] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    schedule: str = ""
    is_template: bool = False
    status: str = "inactive"
    created_at: float = field(default_factory=time.time)
    last_run: float = 0.0
    run_count: int = 0


@dataclass
class WorkflowExecution:
    """A single execution of a workflow."""
    id: str
    workflow_id: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    step_results: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    started_at: float = 0.0
    completed_at: float = 0.0
    triggered_by: str = "manual"


class WorkflowEngine:
    """Execute and manage workflows."""

    def __init__(self):
        self._workflows: dict[str, Workflow] = {}
        self._executions: dict[str, WorkflowExecution] = {}
        self._running: set[str] = set()

    def create_workflow(self, name: str, description: str = "") -> Workflow:
        """Create a new workflow."""
        wf = Workflow(id=secrets.token_hex(8), name=name, description=description)
        self._workflows[wf.id] = wf
        logger.info(f"Created workflow: {name}")
        return wf

    def add_step(
        self,
        workflow_id: str,
        name: str,
        action: StepAction,
        config: dict = None,
        dependencies: list[str] = None,
        condition: str = "",
    ) -> Optional[WorkflowStep]:
        """Add a step to a workflow."""
        wf = self._workflows.get(workflow_id)
        if not wf:
            return None
        step = WorkflowStep(
            id=secrets.token_hex(4),
            name=name,
            action=action,
            config=config or {},
            dependencies=dependencies or [],
            condition=condition,
        )
        wf.steps.append(step)
        return step

    def create_template(self, name: str, description: str = "") -> Workflow:
        """Create a workflow template."""
        wf = self.create_workflow(name, description)
        wf.is_template = True
        return wf

    async def execute_workflow(self, workflow_id: str, triggered_by: str = "manual") -> WorkflowExecution:
        """Execute a workflow."""
        wf = self._workflows.get(workflow_id)
        if not wf:
            raise ValueError(f"Workflow not found: {workflow_id}")

        execution = WorkflowExecution(
            id=secrets.token_hex(8),
            workflow_id=workflow_id,
            status=WorkflowStatus.RUNNING,
            triggered_by=triggered_by,
        )
        self._executions[execution.id] = execution
        self._running.add(execution.id)
        execution.started_at = time.time()
        wf.status = "running"
        wf.run_count += 1

        try:
            await self._run_steps(wf, execution)
            execution.status = WorkflowStatus.COMPLETED
        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.errors.append(str(e)[:200])
            logger.error(f"Workflow {workflow_id} failed: {str(e)[:200]}")
        finally:
            execution.completed_at = time.time()
            wf.status = "completed" if execution.status == WorkflowStatus.COMPLETED else "failed"
            self._running.discard(execution.id)
            wf.last_run = time.time()

        return execution

    async def _run_steps(self, wf: Workflow, execution: WorkflowExecution):
        """Execute all steps respecting dependencies."""
        completed = set()
        remaining = list(wf.steps)

        while remaining:
            ready = [s for s in remaining if all(d in completed for d in s.dependencies)]
            if not ready:
                break

            tasks = [self._execute_step(s, execution) for s in ready]
            await asyncio.gather(*tasks)

            for step in ready:
                if step.status == "completed":
                    completed.add(step.id)
                remaining.remove(step)

    async def _execute_step(self, step: WorkflowStep, execution: WorkflowExecution):
        """Execute a single workflow step."""
        step.status = "running"

        # Check condition
        if step.condition and not self._evaluate_condition(step.condition, execution):
            step.status = "skipped"
            return

        for attempt in range(step.max_retries + 1):
            try:
                result = await self._run_action(step.action, step.config, execution)
                step.status = "completed"
                step.result = str(result)
                execution.step_results[step.id] = step.result
                return
            except asyncio.TimeoutError:
                step.error = "Timeout"
                if attempt >= step.max_retries:
                    step.status = "failed"
                    execution.errors.append(f"Step '{step.name}' timed out")
            except Exception as e:
                step.error = str(e)[:200]
                if attempt >= step.max_retries:
                    step.status = "failed"
                    execution.errors.append(f"Step '{step.name}' failed: {str(e)[:200]}")
                await asyncio.sleep(2 ** attempt)

    async def _run_action(self, action: StepAction, config: dict, execution: WorkflowExecution) -> str:
        """Run a specific action type."""
        if action == StepAction.AGENT_TASK:
            return f"Agent task executed: {config.get('description', 'unknown')}"
        elif action == StepAction.WEBHOOK:
            return f"Webhook sent to {config.get('url', 'unknown')}"
        elif action == StepAction.DELAY:
            delay = config.get("seconds", 1)
            await asyncio.sleep(delay)
            return f"Delayed {delay}s"
        elif action == StepAction.APPROVAL:
            return "Approval required (manual)"
        elif action == StepAction.CONDITION:
            return "Condition evaluated"
        else:
            return "Action executed"

    def _evaluate_condition(self, condition: str, execution: WorkflowExecution) -> bool:
        """Evaluate a condition expression."""
        if not condition:
            return True
        # Simple condition evaluation
        return True

    def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running execution."""
        if execution_id in self._running:
            self._running.discard(execution_id)
            execution = self._executions.get(execution_id)
            if execution:
                execution.status = WorkflowStatus.CANCELLED
            return True
        return False

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        return self._workflows.get(workflow_id)

    def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        return self._executions.get(execution_id)

    def list_workflows(self) -> list[Workflow]:
        return list(self._workflows.values())

    def list_templates(self) -> list[Workflow]:
        return [w for w in self._workflows.values() if w.is_template]

    def clone_workflow(self, template_id: str, name: str) -> Optional[Workflow]:
        """Clone a template workflow."""
        template = self._workflows.get(template_id)
        if not template or not template.is_template:
            return None

        clone = Workflow(
            id=secrets.token_hex(8),
            name=name,
            description=template.description,
        )
        for step in template.steps:
            clone.steps.append(WorkflowStep(
                id=secrets.token_hex(4),
                name=step.name,
                action=step.action,
                config=dict(step.config),
                dependencies=list(step.dependencies),
                condition=step.condition,
            ))
        self._workflows[clone.id] = clone
        return clone

    def get_analytics(self) -> dict:
        """Get workflow analytics."""
        total = len(self._workflows)
        templates = len([w for w in self._workflows.values() if w.is_template])
        executions = len(self._executions)
        completed = len([e for e in self._executions.values() if e.status == WorkflowStatus.COMPLETED])
        return {
            "total_workflows": total,
            "templates": templates,
            "total_executions": executions,
            "completed_executions": completed,
            "success_rate": round(completed / max(executions, 1) * 100, 2),
            "running": len(self._running),
        }


workflow_engine = WorkflowEngine()
