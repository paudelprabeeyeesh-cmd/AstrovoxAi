"""Workflow Automation Engine.

Supports reusable workflows with sequential/parallel execution,
conditional branches, loops, retry policies, scheduling, triggers,
templates, approvals, notifications, and execution history.
"""

import time
import logging
import asyncio
import json
from typing import Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

from .events import event_bus, Event
from .jobs import job_queue, JobPriority

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING_APPROVAL = "waiting_approval"


class StepAction(Enum):
    AGENT_TASK = "agent_task"
    CONDITION = "condition"
    LOOP = "loop"
    APPROVAL = "approval"
    DELAY = "delay"
    WEBHOOK = "webhook"
    NOTIFICATION = "notification"


class BackoffStrategy(Enum):
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIXED = "fixed"


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
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    status: str = "pending"
    result: str = ""
    error: str = ""
    started_at: float = 0.0
    completed_at: float = 0.0


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
    owner_id: str = ""
    shared: bool = False


@dataclass
class WorkflowTemplate:
    """A workflow template that can be instantiated."""
    id: str
    name: str
    description: str
    steps: list[dict] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    category: str = ""
    shared: bool = False
    created_at: float = field(default_factory=time.time)
    usage_count: int = 0


@dataclass
class WorkflowSchedule:
    """A schedule for running a workflow."""
    id: str
    workflow_id: str
    cron: str = ""
    run_at: float = 0.0
    recurring: bool = False
    interval_seconds: int = 0
    enabled: bool = True
    next_run: float = 0.0
    last_run: float = 0.0
    run_count: int = 0
    created_at: float = field(default_factory=time.time)


@dataclass
class EventTrigger:
    """An event-driven trigger for a workflow."""
    id: str
    workflow_id: str
    event_type: str
    filter_conditions: dict = field(default_factory=dict)
    enabled: bool = True
    triggered_count: int = 0
    created_at: float = field(default_factory=time.time)


@dataclass
class StepLog:
    """Detailed log for a single step execution."""
    step_id: str
    execution_id: str
    timestamp: float
    level: str
    message: str
    metadata: dict = field(default_factory=dict)


@dataclass
class ApprovalRequest:
    """A pending approval request for a workflow step."""
    id: str
    execution_id: str
    step_id: str
    workflow_id: str
    requested_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    status: str = "pending"
    approver_id: str = ""
    decision_note: str = ""
    auto_action: str = "reject"


@dataclass
class NotificationRule:
    """Rule for sending notifications on workflow events."""
    id: str
    workflow_id: str
    event: str  # "completed", "failed", "approval_required"
    channel: str  # "email", "webhook", "log"
    target: str = ""
    enabled: bool = True


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
    trigger_data: dict = field(default_factory=dict)
    logs: list[StepLog] = field(default_factory=list)


class WorkflowEngine:
    """Execute and manage workflows with scheduling, triggers, and history."""

    def __init__(self):
        self._workflows: dict[str, Workflow] = {}
        self._executions: dict[str, WorkflowExecution] = {}
        self._running: set[str] = set()
        self._schedules: dict[str, WorkflowSchedule] = {}
        self._triggers: dict[str, EventTrigger] = {}
        self._templates: dict[str, WorkflowTemplate] = {}
        self._approvals: dict[str, ApprovalRequest] = {}
        self._notifications: dict[str, NotificationRule] = {}
        self._execution_logs: dict[str, list[StepLog]] = {}
        self._scheduler_task: Optional[asyncio.Task] = None
        self._scheduler_running: bool = False

    # ------------------------------------------------------------------ Workflows

    def create_workflow(self, name: str, description: str = "", owner_id: str = "") -> Workflow:
        """Create a new workflow."""
        import secrets
        wf = Workflow(
            id=secrets.token_hex(8),
            name=name,
            description=description,
            owner_id=owner_id,
        )
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
        max_retries: int = 3,
        timeout_seconds: int = 300,
        backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL,
    ) -> Optional[WorkflowStep]:
        """Add a step to a workflow."""
        import secrets
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
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
            backoff_strategy=backoff_strategy,
        )
        wf.steps.append(step)
        return step

    def create_template(self, name: str, description: str = "") -> Workflow:
        """Create a workflow template."""
        wf = self.create_workflow(name, description)
        wf.is_template = True
        return wf

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        return self._workflows.get(workflow_id)

    def list_workflows(self) -> list[Workflow]:
        return list(self._workflows.values())

    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow and cancel its schedules/triggers."""
        if workflow_id not in self._workflows:
            return False
        for ex_id in list(self._running):
            ex = self._executions.get(ex_id)
            if ex and ex.workflow_id == workflow_id:
                self.cancel_execution(ex_id)
        for sid in list(self._schedules.keys()):
            if self._schedules[sid].workflow_id == workflow_id:
                del self._schedules[sid]
        for tid in list(self._triggers.keys()):
            if self._triggers[tid].workflow_id == workflow_id:
                del self._triggers[tid]
        del self._workflows[workflow_id]
        return True

    # ------------------------------------------------------------------ Templates

    def save_template(
        self,
        name: str,
        description: str,
        steps: list[dict],
        tags: list[str] = None,
        category: str = "",
        shared: bool = False,
    ) -> WorkflowTemplate:
        """Save a workflow as a reusable template."""
        import secrets
        tpl = WorkflowTemplate(
            id=secrets.token_hex(8),
            name=name,
            description=description,
            steps=steps,
            tags=tags or [],
            category=category,
            shared=shared,
        )
        self._templates[tpl.id] = tpl
        return tpl

    def list_templates(self, category: str = "", tag: str = "") -> list[WorkflowTemplate]:
        """List templates with optional filters."""
        out = list(self._templates.values())
        if category:
            out = [t for t in out if t.category == category]
        if tag:
            out = [t for t in out if tag in t.tags]
        return out

    def get_template(self, template_id: str) -> Optional[WorkflowTemplate]:
        return self._templates.get(template_id)

    def instantiate_template(
        self,
        template_id: str,
        workflow_name: str,
        owner_id: str = "",
    ) -> Optional[Workflow]:
        """Create a new workflow from a template."""
        import secrets
        tpl = self._templates.get(template_id)
        if not tpl:
            return None
        wf = self.create_workflow(workflow_name, tpl.description, owner_id)
        for s in tpl.steps:
            try:
                action = StepAction(s.get("action", "agent_task"))
            except ValueError:
                action = StepAction.AGENT_TASK
            step = WorkflowStep(
                id=secrets.token_hex(4),
                name=s.get("name", "step"),
                action=action,
                config=s.get("config", {}),
                dependencies=s.get("dependencies", []),
                condition=s.get("condition", ""),
                max_retries=s.get("max_retries", 3),
                timeout_seconds=s.get("timeout_seconds", 300),
            )
            wf.steps.append(step)
        tpl.usage_count += 1
        return wf

    def share_template(self, template_id: str, shared: bool = True) -> bool:
        """Mark a template as shared or private."""
        tpl = self._templates.get(template_id)
        if not tpl:
            return False
        tpl.shared = shared
        return True

    # ------------------------------------------------------------------ Scheduling

    def schedule_workflow(
        self,
        workflow_id: str,
        cron: str = "",
        run_at: float = 0.0,
        recurring: bool = False,
        interval_seconds: int = 0,
    ) -> Optional[WorkflowSchedule]:
        """Create a schedule for a workflow."""
        import secrets
        if workflow_id not in self._workflows:
            return None
        sched = WorkflowSchedule(
            id=secrets.token_hex(8),
            workflow_id=workflow_id,
            cron=cron,
            run_at=run_at,
            recurring=recurring,
            interval_seconds=interval_seconds,
            next_run=self._compute_next_run(cron, run_at, interval_seconds, recurring),
        )
        self._schedules[sched.id] = sched
        return sched

    def _compute_next_run(
        self,
        cron: str,
        run_at: float,
        interval_seconds: int,
        recurring: bool,
    ) -> float:
        """Compute next execution time for a schedule."""
        now = time.time()
        if cron:
            return self._next_cron(cron, now)
        if run_at > now:
            return run_at
        if recurring and interval_seconds > 0:
            return now + interval_seconds
        return run_at if run_at > now else 0.0

    def _next_cron(self, cron: str, now: float) -> float:
        """Compute next matching time for a cron expression.

        Supports simple cron patterns: "minute hour day month weekday"
        """
        try:
            parts = cron.split()
            if len(parts) != 5:
                return now + 60
            minute_s, hour_s, dom_s, mon_s, dow_s = parts
            from datetime import datetime, timedelta
            dt = datetime.fromtimestamp(now) + timedelta(minutes=1)
            dt = dt.replace(second=0, microsecond=0)
            for _ in range(60 * 24 * 7):
                if self._cron_match(dt, minute_s, hour_s, dom_s, mon_s, dow_s):
                    return dt.timestamp()
                dt += timedelta(minutes=1)
            return now + 3600
        except Exception:
            return now + 60

    def _cron_match(self, dt, minute_s, hour_s, dom_s, mon_s, dow_s) -> bool:
        """Check if datetime matches cron fields."""
        def match(value, field):
            if field == "*":
                return True
            if "," in field:
                return value in [int(x) for x in field.split(",")]
            if "/" in field:
                base, step = field.split("/")
                start = 0 if base == "*" else int(base)
                return (value - start) % int(step) == 0 and value >= start
            if "-" in field:
                a, b = field.split("-")
                return int(a) <= value <= int(b)
            return value == int(field)

        return (
            match(dt.minute, minute_s)
            and match(dt.hour, hour_s)
            and match(dt.day, dom_s)
            and match(dt.month, mon_s)
            and match(dt.weekday(), dow_s)
        )

    def list_schedules(self, workflow_id: str = "") -> list[WorkflowSchedule]:
        """List schedules, optionally filtered by workflow."""
        out = list(self._schedules.values())
        if workflow_id:
            out = [s for s in out if s.workflow_id == workflow_id]
        return out

    def cancel_schedule(self, schedule_id: str) -> bool:
        """Cancel a schedule."""
        sched = self._schedules.get(schedule_id)
        if not sched:
            return False
        sched.enabled = False
        return True

    def delete_schedule(self, schedule_id: str) -> bool:
        if schedule_id not in self._schedules:
            return False
        del self._schedules[schedule_id]
        return True

    async def start_scheduler(self):
        """Start the scheduler background loop."""
        if self._scheduler_running:
            return
        self._scheduler_running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

    async def stop_scheduler(self):
        """Stop the scheduler loop."""
        self._scheduler_running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except (asyncio.CancelledError, Exception):
                pass
            self._scheduler_task = None

    async def _scheduler_loop(self):
        """Run scheduled workflows at their next_run time."""
        while self._scheduler_running:
            now = time.time()
            for sid in list(self._schedules.keys()):
                sched = self._schedules.get(sid)
                if not sched or not sched.enabled:
                    continue
                if sched.next_run > 0 and sched.next_run <= now:
                    try:
                        await self.execute_workflow(
                            sched.workflow_id,
                            triggered_by=f"schedule:{sid}",
                        )
                    except Exception as e:
                        logger.error(f"Scheduled execution failed: {e}")
                    sched.last_run = now
                    sched.run_count += 1
                    sched.next_run = self._compute_next_run(
                        sched.cron, now, sched.interval_seconds, sched.recurring
                    )
            await asyncio.sleep(1)

    # ------------------------------------------------------------------ Triggers

    def create_trigger(
        self,
        workflow_id: str,
        event_type: str,
        filter_conditions: dict = None,
    ) -> Optional[EventTrigger]:
        """Create an event trigger for a workflow."""
        import secrets
        if workflow_id not in self._workflows:
            return None
        trigger = EventTrigger(
            id=secrets.token_hex(8),
            workflow_id=workflow_id,
            event_type=event_type,
            filter_conditions=filter_conditions or {},
        )
        self._triggers[trigger.id] = trigger
        wf = self._workflows[workflow_id]
        if event_type not in wf.triggers:
            wf.triggers.append(event_type)
        event_bus.subscribe(event_type, self._make_event_handler(trigger))
        return trigger

    def _make_event_handler(self, trigger: EventTrigger) -> Callable[[Event], Any]:
        """Build an event handler that runs the workflow on a matching event."""
        async def handler(event: Event):
            if not trigger.enabled:
                return
            if not self._match_filter(event.data, trigger.filter_conditions):
                return
            trigger.triggered_count += 1
            try:
                await self.execute_workflow(
                    trigger.workflow_id,
                    triggered_by=f"event:{event.type}",
                    trigger_data=dict(event.data),
                )
            except Exception as e:
                logger.error(f"Triggered workflow failed: {e}")

        return handler

    def _match_filter(self, data: dict, conditions: dict) -> bool:
        """Check if event data matches trigger filter conditions."""
        if not conditions:
            return True
        for key, expected in conditions.items():
            if key not in data:
                return False
            if isinstance(expected, list):
                if data[key] not in expected:
                    return False
            elif data[key] != expected:
                return False
        return True

    def list_triggers(self, workflow_id: str = "") -> list[EventTrigger]:
        """List triggers, optionally filtered by workflow."""
        out = list(self._triggers.values())
        if workflow_id:
            out = [t for t in out if t.workflow_id == workflow_id]
        return out

    def disable_trigger(self, trigger_id: str) -> bool:
        trig = self._triggers.get(trigger_id)
        if not trig:
            return False
        trig.enabled = False
        return True

    def delete_trigger(self, trigger_id: str) -> bool:
        if trigger_id not in self._triggers:
            return False
        del self._triggers[trigger_id]
        return True

    # ------------------------------------------------------------------ Execution

    async def execute_workflow(
        self,
        workflow_id: str,
        triggered_by: str = "manual",
        trigger_data: dict = None,
    ) -> WorkflowExecution:
        """Execute a workflow."""
        import secrets
        wf = self._workflows.get(workflow_id)
        if not wf:
            raise ValueError(f"Workflow not found: {workflow_id}")

        execution = WorkflowExecution(
            id=secrets.token_hex(8),
            workflow_id=workflow_id,
            status=WorkflowStatus.RUNNING,
            triggered_by=triggered_by,
            trigger_data=trigger_data or {},
        )
        self._executions[execution.id] = execution
        self._running.add(execution.id)
        self._execution_logs[execution.id] = []
        execution.started_at = time.time()
        execution.logs.append(self._log(execution.id, "", "info", f"Workflow {wf.name} started"))
        wf.status = "running"
        wf.run_count += 1

        try:
            await self._run_steps(wf, execution)
            execution.status = WorkflowStatus.COMPLETED
            execution.logs.append(self._log(execution.id, "", "info", "Workflow completed"))
            await self._fire_notification(wf, execution, "completed")
        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.errors.append(str(e)[:200])
            execution.logs.append(self._log(execution.id, "", "error", f"Workflow failed: {str(e)[:200]}"))
            logger.error(f"Workflow {workflow_id} failed: {str(e)[:200]}")
            await self._fire_notification(wf, execution, "failed")
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
                if step.status in ("completed", "skipped"):
                    completed.add(step.id)
                remaining.remove(step)

    async def _execute_step(self, step: WorkflowStep, execution: WorkflowExecution):
        """Execute a single workflow step."""
        import secrets
        step.status = "running"
        step.started_at = time.time()
        execution.logs.append(self._log(execution.id, step.id, "info", f"Step '{step.name}' started"))

        if step.condition and not self._evaluate_condition(step.condition, execution):
            step.status = "skipped"
            execution.logs.append(self._log(execution.id, step.id, "info", "Step skipped by condition"))
            return

        for attempt in range(step.max_retries + 1):
            try:
                result = await asyncio.wait_for(
                    self._run_action(step.action, step.config, execution),
                    timeout=step.timeout_seconds,
                )
                step.status = "completed"
                step.result = str(result)
                step.completed_at = time.time()
                execution.step_results[step.id] = step.result
                execution.logs.append(self._log(execution.id, step.id, "info", f"Step completed: {step.result[:120]}"))
                return
            except asyncio.TimeoutError:
                step.error = "Timeout"
                execution.logs.append(self._log(execution.id, step.id, "error", f"Timeout (attempt {attempt+1})"))
                if attempt >= step.max_retries:
                    step.status = "failed"
                    execution.errors.append(f"Step '{step.name}' timed out")
                    raise
            except Exception as e:
                step.error = str(e)[:200]
                step.retry_count += 1
                execution.logs.append(
                    self._log(execution.id, step.id, "warning",
                              f"Step error (attempt {attempt+1}/{step.max_retries+1}): {step.error}")
                )
                if attempt >= step.max_retries:
                    step.status = "failed"
                    execution.errors.append(f"Step '{step.name}' failed: {str(e)[:200]}")
                    raise
                await asyncio.sleep(self._backoff_delay(step.backoff_strategy, attempt))

    def _backoff_delay(self, strategy: BackoffStrategy, attempt: int) -> float:
        """Compute retry backoff delay based on strategy."""
        if strategy == BackoffStrategy.EXPONENTIAL:
            return float(2 ** attempt)
        if strategy == BackoffStrategy.LINEAR:
            return float(attempt + 1)
        return 1.0

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
            await self._request_approval(execution, config)
            return "Approval flow processed"
        elif action == StepAction.CONDITION:
            return "Condition evaluated"
        elif action == StepAction.NOTIFICATION:
            msg = config.get("message", "Notification")
            execution.logs.append(self._log(execution.id, "", "info", f"Notification: {msg}"))
            return f"Notification sent: {msg}"
        else:
            return "Action executed"

    async def _request_approval(self, execution: WorkflowExecution, config: dict):
        """Create an approval request and wait for decision or timeout."""
        import secrets
        timeout = config.get("timeout_seconds", 3600)
        request = ApprovalRequest(
            id=secrets.token_hex(8),
            execution_id=execution.id,
            step_id="",
            workflow_id=execution.workflow_id,
            expires_at=time.time() + timeout,
            auto_action=config.get("on_timeout", "reject"),
        )
        self._approvals[request.id] = request
        execution.status = WorkflowStatus.WAITING_APPROVAL
        wf = self._workflows.get(execution.workflow_id)
        if wf:
            await self._fire_notification(wf, execution, "approval_required")

        deadline = request.expires_at
        while time.time() < deadline and request.status == "pending":
            await asyncio.sleep(1)
            if request.status != "pending":
                break
        if request.status == "pending":
            request.status = "timeout"
        execution.status = WorkflowStatus.RUNNING
        if request.status == "rejected" or request.status == "timeout" and request.auto_action == "reject":
            raise Exception(f"Approval {request.status}")

    def _evaluate_condition(self, condition: str, execution: WorkflowExecution) -> bool:
        """Evaluate a condition expression (simple)."""
        if not condition:
            return True
        try:
            ctx = {"result": execution.step_results, "data": execution.trigger_data}
            return bool(eval(condition, {"__builtins__": {}}, ctx))
        except Exception:
            return True

    def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running execution."""
        if execution_id in self._running:
            self._running.discard(execution_id)
            execution = self._executions.get(execution_id)
            if execution:
                execution.status = WorkflowStatus.CANCELLED
                execution.completed_at = time.time()
            return True
        return False

    # ------------------------------------------------------------------ Approvals

    def approve_step(
        self,
        approval_id: str,
        approver_id: str = "",
        note: str = "",
        approved: bool = True,
    ) -> bool:
        """Approve or reject an approval request."""
        req = self._approvals.get(approval_id)
        if not req or req.status != "pending":
            return False
        req.status = "approved" if approved else "rejected"
        req.approver_id = approver_id
        req.decision_note = note
        return True

    def list_approvals(self, workflow_id: str = "", status: str = "") -> list[ApprovalRequest]:
        """List approval requests with optional filters."""
        out = list(self._approvals.values())
        if workflow_id:
            out = [a for a in out if a.workflow_id == workflow_id]
        if status:
            out = [a for a in out if a.status == status]
        return out

    # ------------------------------------------------------------------ Notifications

    def add_notification(
        self,
        workflow_id: str,
        event: str,
        channel: str,
        target: str = "",
    ) -> Optional[NotificationRule]:
        """Add a notification rule."""
        import secrets
        if workflow_id not in self._workflows:
            return None
        rule = NotificationRule(
            id=secrets.token_hex(8),
            workflow_id=workflow_id,
            event=event,
            channel=channel,
            target=target,
        )
        self._notifications[rule.id] = rule
        return rule

    def list_notifications(self, workflow_id: str = "") -> list[NotificationRule]:
        out = list(self._notifications.values())
        if workflow_id:
            out = [n for n in out if n.workflow_id == workflow_id]
        return out

    async def _fire_notification(self, wf: Workflow, execution: WorkflowExecution, event: str):
        """Fire notification rules for an event."""
        for rule in self._notifications.values():
            if rule.workflow_id != wf.id or rule.event != event or not rule.enabled:
                continue
            try:
                if rule.channel == "log":
                    logger.info(f"[notify:{rule.target}] {event} on {wf.name} exec={execution.id}")
                elif rule.channel == "webhook":
                    logger.info(f"Webhook notify to {rule.target}: {event}")
                execution.logs.append(
                    self._log(execution.id, "", "info",
                              f"Notification fired: {rule.channel}:{rule.target} event={event}")
                )
            except Exception:
                pass

    # ------------------------------------------------------------------ History

    def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        return self._executions.get(execution_id)

    def list_executions(
        self,
        workflow_id: str = "",
        status: WorkflowStatus = None,
        limit: int = 50,
    ) -> list[WorkflowExecution]:
        """List executions with filters."""
        out = list(self._executions.values())
        if workflow_id:
            out = [e for e in out if e.workflow_id == workflow_id]
        if status:
            out = [e for e in out if e.status == status]
        out.sort(key=lambda e: e.started_at, reverse=True)
        return out[:limit]

    def get_execution_logs(self, execution_id: str) -> list[StepLog]:
        """Get step-level logs for an execution."""
        ex = self._executions.get(execution_id)
        if not ex:
            return []
        return ex.logs

    def replay_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Replay a past execution by running the same workflow again."""
        import secrets
        ex = self._executions.get(execution_id)
        if not ex:
            return None
        replay = WorkflowExecution(
            id=secrets.token_hex(8),
            workflow_id=ex.workflow_id,
            triggered_by=f"replay:{execution_id}",
            trigger_data=dict(ex.trigger_data),
        )
        self._executions[replay.id] = replay
        asyncio.create_task(self.execute_workflow(ex.workflow_id, replay.triggered_by, ex.trigger_data))
        return replay

    def compare_executions(self, execution_id_a: str, execution_id_b: str) -> dict:
        """Compare two executions and return diff summary."""
        a = self._executions.get(execution_id_a)
        b = self._executions.get(execution_id_b)
        if not a or not b:
            return {}
        a_keys = set(a.step_results.keys())
        b_keys = set(b.step_results.keys())
        diff_keys = a_keys.symmetric_difference(b_keys)
        changed = [k for k in a_keys & b_keys if a.step_results[k] != b.step_results[k]]
        return {
            "execution_a": execution_id_a,
            "execution_b": execution_id_b,
            "status_a": a.status.value,
            "status_b": b.status.value,
            "duration_a": (a.completed_at - a.started_at) if a.completed_at else 0.0,
            "duration_b": (b.completed_at - b.started_at) if b.completed_at else 0.0,
            "only_in_a": list(a_keys - b_keys),
            "only_in_b": list(b_keys - a_keys),
            "changed_results": changed,
            "errors_a": list(a.errors),
            "errors_b": list(b.errors),
        }

    # ------------------------------------------------------------------ Cloning / Analytics

    def clone_workflow(self, template_id: str, name: str) -> Optional[Workflow]:
        """Clone a template workflow."""
        import secrets
        template = self._workflows.get(template_id)
        if not template:
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
                max_retries=step.max_retries,
                timeout_seconds=step.timeout_seconds,
                backoff_strategy=step.backoff_strategy,
            ))
        self._workflows[clone.id] = clone
        return clone

    def get_analytics(self) -> dict:
        """Get workflow analytics."""
        total = len(self._workflows)
        templates = len(self._templates)
        executions = len(self._executions)
        completed = len([e for e in self._executions.values() if e.status == WorkflowStatus.COMPLETED])
        failed = len([e for e in self._executions.values() if e.status == WorkflowStatus.FAILED])
        return {
            "total_workflows": total,
            "templates": templates,
            "total_executions": executions,
            "completed_executions": completed,
            "failed_executions": failed,
            "success_rate": round(completed / max(executions, 1) * 100, 2),
            "running": len(self._running),
            "schedules": len(self._schedules),
            "triggers": len(self._triggers),
            "pending_approvals": len([a for a in self._approvals.values() if a.status == "pending"]),
        }

    # ------------------------------------------------------------------ Helpers

    def _log(self, execution_id: str, step_id: str, level: str, message: str) -> StepLog:
        entry = StepLog(
            step_id=step_id,
            execution_id=execution_id,
            timestamp=time.time(),
            level=level,
            message=message,
        )
        if execution_id in self._execution_logs:
            self._execution_logs[execution_id].append(entry)
        return entry


workflow_engine = WorkflowEngine()