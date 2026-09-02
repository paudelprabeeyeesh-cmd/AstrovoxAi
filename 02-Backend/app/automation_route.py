"""Automation Center API — workflows, templates, schedules, triggers, executions."""

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional

from .auth_utils import get_user_id_from_token
from .workflow_engine import (
    workflow_engine,
    WorkflowEngine,
    Workflow,
    WorkflowTemplate,
    WorkflowSchedule,
    EventTrigger,
    ApprovalRequest,
    NotificationRule,
    WorkflowExecution,
    StepAction,
    BackoffStrategy,
    WorkflowStatus,
)

router = APIRouter(prefix="/api/automation", tags=["automation"])


class CreateWorkflowRequest(BaseModel):
    name: str
    description: str = ""
    owner_id: str = ""


class AddStepRequest(BaseModel):
    name: str
    action: str = "agent_task"
    config: dict = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)
    condition: str = ""
    max_retries: int = 3
    timeout_seconds: int = 300
    backoff_strategy: str = "exponential"


class ScheduleWorkflowRequest(BaseModel):
    cron: str = ""
    run_at: float = 0.0
    recurring: bool = False
    interval_seconds: int = 0


class ExecuteWorkflowRequest(BaseModel):
    trigger_data: dict = Field(default_factory=dict)


class CreateTemplateRequest(BaseModel):
    name: str
    description: str = ""
    steps: list[dict] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    category: str = ""
    shared: bool = False


class InstantiateTemplateRequest(BaseModel):
    workflow_name: str
    owner_id: str = ""


class CreateTriggerRequest(BaseModel):
    workflow_id: str
    event_type: str
    filter_conditions: dict = Field(default_factory=dict)


class AddNotificationRequest(BaseModel):
    workflow_id: str
    event: str
    channel: str
    target: str = ""


class ApprovalDecisionRequest(BaseModel):
    approver_id: str = ""
    note: str = ""
    approved: bool = True


def _user(authorization: str) -> str:
    return get_user_id_from_token(authorization)


def _workflow_dict(wf: Workflow) -> dict:
    return {
        "id": wf.id,
        "name": wf.name,
        "description": wf.description,
        "is_template": wf.is_template,
        "status": wf.status,
        "schedule": wf.schedule,
        "triggers": wf.triggers,
        "steps": [
            {
                "id": s.id,
                "name": s.name,
                "action": s.action.value if hasattr(s.action, "value") else str(s.action),
                "config": s.config,
                "dependencies": s.dependencies,
                "condition": s.condition,
                "max_retries": s.max_retries,
                "timeout_seconds": s.timeout_seconds,
                "backoff_strategy": s.backoff_strategy.value if hasattr(s.backoff_strategy, "value") else str(s.backoff_strategy),
                "status": s.status,
            }
            for s in wf.steps
        ],
        "created_at": wf.created_at,
        "last_run": wf.last_run,
        "run_count": wf.run_count,
        "owner_id": wf.owner_id,
        "shared": wf.shared,
    }


def _execution_dict(ex: WorkflowExecution) -> dict:
    return {
        "id": ex.id,
        "workflow_id": ex.workflow_id,
        "status": ex.status.value if hasattr(ex.status, "value") else str(ex.status),
        "step_results": ex.step_results,
        "errors": ex.errors,
        "started_at": ex.started_at,
        "completed_at": ex.completed_at,
        "triggered_by": ex.triggered_by,
        "duration": (ex.completed_at - ex.started_at) if ex.completed_at else 0.0,
    }


def _template_dict(t: WorkflowTemplate) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "description": t.description,
        "steps": t.steps,
        "tags": t.tags,
        "category": t.category,
        "shared": t.shared,
        "created_at": t.created_at,
        "usage_count": t.usage_count,
    }


def _schedule_dict(s: WorkflowSchedule) -> dict:
    return {
        "id": s.id,
        "workflow_id": s.workflow_id,
        "cron": s.cron,
        "run_at": s.run_at,
        "recurring": s.recurring,
        "interval_seconds": s.interval_seconds,
        "enabled": s.enabled,
        "next_run": s.next_run,
        "last_run": s.last_run,
        "run_count": s.run_count,
    }


def _trigger_dict(t: EventTrigger) -> dict:
    return {
        "id": t.id,
        "workflow_id": t.workflow_id,
        "event_type": t.event_type,
        "filter_conditions": t.filter_conditions,
        "enabled": t.enabled,
        "triggered_count": t.triggered_count,
        "created_at": t.created_at,
    }


def _approval_dict(a: ApprovalRequest) -> dict:
    return {
        "id": a.id,
        "execution_id": a.execution_id,
        "workflow_id": a.workflow_id,
        "status": a.status,
        "approver_id": a.approver_id,
        "decision_note": a.decision_note,
        "requested_at": a.requested_at,
        "expires_at": a.expires_at,
    }


def _notification_dict(n: NotificationRule) -> dict:
    return {
        "id": n.id,
        "workflow_id": n.workflow_id,
        "event": n.event,
        "channel": n.channel,
        "target": n.target,
        "enabled": n.enabled,
    }


# ============================================================================
# Workflows
# ============================================================================

@router.post("/workflows")
async def create_workflow(request: CreateWorkflowRequest, authorization: str = Header(None)):
    """Create a new workflow."""
    _user(authorization)
    wf = workflow_engine.create_workflow(
        name=request.name,
        description=request.description,
        owner_id=request.owner_id,
    )
    return {"status": "OK", "workflow": _workflow_dict(wf)}


@router.get("/workflows")
async def list_workflows(authorization: str = Header(None)):
    """List all workflows."""
    _user(authorization)
    return {"status": "OK", "workflows": [_workflow_dict(w) for w in workflow_engine.list_workflows()]}


@router.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str, authorization: str = Header(None)):
    """Get a workflow by ID."""
    _user(authorization)
    wf = workflow_engine.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    return {"status": "OK", "workflow": _workflow_dict(wf)}


@router.delete("/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str, authorization: str = Header(None)):
    """Delete a workflow."""
    _user(authorization)
    if not workflow_engine.delete_workflow(workflow_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    return {"status": "OK", "message": "Workflow deleted"}


@router.post("/workflows/{workflow_id}/steps")
async def add_workflow_step(workflow_id: str, request: AddStepRequest, authorization: str = Header(None)):
    """Add a step to a workflow."""
    _user(authorization)
    try:
        action = StepAction(request.action)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid action: {request.action}")
    try:
        strategy = BackoffStrategy(request.backoff_strategy)
    except ValueError:
        strategy = BackoffStrategy.EXPONENTIAL
    step = workflow_engine.add_step(
        workflow_id=workflow_id,
        name=request.name,
        action=action,
        config=request.config,
        dependencies=request.dependencies,
        condition=request.condition,
        max_retries=request.max_retries,
        timeout_seconds=request.timeout_seconds,
        backoff_strategy=strategy,
    )
    if not step:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    return {"status": "OK", "step_id": step.id}


@router.post("/workflows/{workflow_id}/execute")
async def execute_workflow(workflow_id: str, request: ExecuteWorkflowRequest, authorization: str = Header(None)):
    """Execute a workflow."""
    _user(authorization)
    try:
        ex = await workflow_engine.execute_workflow(
            workflow_id=workflow_id,
            triggered_by="api",
            trigger_data=request.trigger_data,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return {"status": "OK", "execution": _execution_dict(ex)}


@router.post("/workflows/{workflow_id}/schedule")
async def schedule_workflow(workflow_id: str, request: ScheduleWorkflowRequest, authorization: str = Header(None)):
    """Schedule a workflow for execution."""
    _user(authorization)
    sched = workflow_engine.schedule_workflow(
        workflow_id=workflow_id,
        cron=request.cron,
        run_at=request.run_at,
        recurring=request.recurring,
        interval_seconds=request.interval_seconds,
    )
    if not sched:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    return {"status": "OK", "schedule": _schedule_dict(sched)}


@router.get("/workflows/{workflow_id}/executions")
async def list_workflow_executions(
    workflow_id: str,
    authorization: str = Header(None),
    status_filter: Optional[str] = None,
    limit: int = 50,
):
    """List executions for a workflow."""
    _user(authorization)
    st = None
    if status_filter:
        try:
            st = WorkflowStatus(status_filter)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status_filter}")
    execs = workflow_engine.list_executions(workflow_id=workflow_id, status=st, limit=limit)
    return {"status": "OK", "executions": [_execution_dict(e) for e in execs]}


@router.get("/workflows/{workflow_id}/schedules")
async def list_workflow_schedules(workflow_id: str, authorization: str = Header(None)):
    """List schedules for a workflow."""
    _user(authorization)
    return {"status": "OK", "schedules": [_schedule_dict(s) for s in workflow_engine.list_schedules(workflow_id)]}


@router.get("/workflows/{workflow_id}/triggers")
async def list_workflow_triggers(workflow_id: str, authorization: str = Header(None)):
    """List triggers for a workflow."""
    _user(authorization)
    return {"status": "OK", "triggers": [_trigger_dict(t) for t in workflow_engine.list_triggers(workflow_id)]}


# ============================================================================
# Templates
# ============================================================================

@router.post("/templates")
async def create_template(request: CreateTemplateRequest, authorization: str = Header(None)):
    """Create a workflow template."""
    _user(authorization)
    tpl = workflow_engine.save_template(
        name=request.name,
        description=request.description,
        steps=request.steps,
        tags=request.tags,
        category=request.category,
        shared=request.shared,
    )
    return {"status": "OK", "template": _template_dict(tpl)}


@router.get("/templates")
async def list_templates(authorization: str = Header(None), category: str = "", tag: str = ""):
    """List workflow templates."""
    _user(authorization)
    tpls = workflow_engine.list_templates(category=category, tag=tag)
    return {"status": "OK", "templates": [_template_dict(t) for t in tpls]}


@router.get("/templates/{template_id}")
async def get_template(template_id: str, authorization: str = Header(None)):
    """Get a template by ID."""
    _user(authorization)
    tpl = workflow_engine.get_template(template_id)
    if not tpl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return {"status": "OK", "template": _template_dict(tpl)}


@router.post("/templates/{template_id}/instantiate")
async def instantiate_template(template_id: str, request: InstantiateTemplateRequest, authorization: str = Header(None)):
    """Instantiate a workflow from a template."""
    _user(authorization)
    wf = workflow_engine.instantiate_template(
        template_id=template_id,
        workflow_name=request.workflow_name,
        owner_id=request.owner_id,
    )
    if not wf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return {"status": "OK", "workflow": _workflow_dict(wf)}


@router.post("/templates/{template_id}/share")
async def share_template(template_id: str, authorization: str = Header(None), shared: bool = True):
    """Mark a template as shared."""
    _user(authorization)
    if not workflow_engine.share_template(template_id, shared):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return {"status": "OK", "shared": shared}


# ============================================================================
# Triggers
# ============================================================================

@router.post("/triggers")
async def create_trigger(request: CreateTriggerRequest, authorization: str = Header(None)):
    """Create an event-driven trigger for a workflow."""
    _user(authorization)
    trig = workflow_engine.create_trigger(
        workflow_id=request.workflow_id,
        event_type=request.event_type,
        filter_conditions=request.filter_conditions,
    )
    if not trig:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    return {"status": "OK", "trigger": _trigger_dict(trig)}


@router.get("/triggers")
async def list_triggers(authorization: str = Header(None), workflow_id: str = ""):
    """List event triggers."""
    _user(authorization)
    return {"status": "OK", "triggers": [_trigger_dict(t) for t in workflow_engine.list_triggers(workflow_id)]}


@router.post("/triggers/{trigger_id}/disable")
async def disable_trigger(trigger_id: str, authorization: str = Header(None)):
    """Disable a trigger."""
    _user(authorization)
    if not workflow_engine.disable_trigger(trigger_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trigger not found")
    return {"status": "OK"}


@router.delete("/triggers/{trigger_id}")
async def delete_trigger(trigger_id: str, authorization: str = Header(None)):
    """Delete a trigger."""
    _user(authorization)
    if not workflow_engine.delete_trigger(trigger_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trigger not found")
    return {"status": "OK"}


# ============================================================================
# Executions
# ============================================================================

@router.get("/executions")
async def list_executions(authorization: str = Header(None), workflow_id: str = "", limit: int = 50):
    """List executions across all workflows."""
    _user(authorization)
    execs = workflow_engine.list_executions(workflow_id=workflow_id, limit=limit)
    return {"status": "OK", "executions": [_execution_dict(e) for e in execs]}


@router.get("/executions/{execution_id}")
async def get_execution(execution_id: str, authorization: str = Header(None)):
    """Get an execution by ID."""
    _user(authorization)
    ex = workflow_engine.get_execution(execution_id)
    if not ex:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
    return {"status": "OK", "execution": _execution_dict(ex)}


@router.get("/executions/{execution_id}/logs")
async def get_execution_logs(execution_id: str, authorization: str = Header(None)):
    """Get step-level logs for an execution."""
    _user(authorization)
    logs = workflow_engine.get_execution_logs(execution_id)
    if logs is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
    return {
        "status": "OK",
        "logs": [
            {
                "step_id": l.step_id,
                "execution_id": l.execution_id,
                "timestamp": l.timestamp,
                "level": l.level,
                "message": l.message,
                "metadata": l.metadata,
            }
            for l in logs
        ],
    }


@router.post("/executions/{execution_id}/cancel")
async def cancel_execution(execution_id: str, authorization: str = Header(None)):
    """Cancel a running execution."""
    _user(authorization)
    if not workflow_engine.cancel_execution(execution_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot cancel execution")
    return {"status": "OK"}


@router.post("/executions/{execution_id}/replay")
async def replay_execution(execution_id: str, authorization: str = Header(None)):
    """Replay a past execution."""
    _user(authorization)
    replay = workflow_engine.replay_execution(execution_id)
    if not replay:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
    return {"status": "OK", "execution": _execution_dict(replay)}


@router.get("/executions/compare")
async def compare_executions(
    authorization: str = Header(None),
    a: str = "",
    b: str = "",
):
    """Compare two executions."""
    _user(authorization)
    if not a or not b:
        raise HTTPException(status_code=400, detail="Missing execution IDs")
    diff = workflow_engine.compare_executions(a, b)
    if not diff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
    return {"status": "OK", "diff": diff}


# ============================================================================
# Approvals
# ============================================================================

@router.post("/executions/{execution_id}/approve")
async def approve_execution_step(
    execution_id: str,
    request: ApprovalDecisionRequest,
    authorization: str = Header(None),
):
    """Approve or reject a pending approval request for an execution."""
    _user(authorization)
    pending = [a for a in workflow_engine.list_approvals() if a.execution_id == execution_id and a.status == "pending"]
    if not pending:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No pending approval for this execution")
    target = pending[0]
    if not workflow_engine.approve_step(
        approval_id=target.id,
        approver_id=request.approver_id,
        note=request.note,
        approved=request.approved,
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not record approval")
    return {"status": "OK", "approval": _approval_dict(target)}


@router.get("/approvals")
async def list_approvals(authorization: str = Header(None), workflow_id: str = "", status_filter: str = ""):
    """List approval requests."""
    _user(authorization)
    return {"status": "OK", "approvals": [_approval_dict(a) for a in workflow_engine.list_approvals(workflow_id, status_filter)]}


# ============================================================================
# Notifications
# ============================================================================

@router.post("/notifications")
async def add_notification(request: AddNotificationRequest, authorization: str = Header(None)):
    """Add a notification rule."""
    _user(authorization)
    rule = workflow_engine.add_notification(
        workflow_id=request.workflow_id,
        event=request.event,
        channel=request.channel,
        target=request.target,
    )
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    return {"status": "OK", "notification": _notification_dict(rule)}


@router.get("/notifications")
async def list_notifications(authorization: str = Header(None), workflow_id: str = ""):
    """List notification rules."""
    _user(authorization)
    return {"status": "OK", "notifications": [_notification_dict(n) for n in workflow_engine.list_notifications(workflow_id)]}


# ============================================================================
# Analytics
# ============================================================================

@router.get("/analytics")
async def get_automation_analytics(authorization: str = Header(None)):
    """Get automation analytics."""
    _user(authorization)
    return {"status": "OK", "analytics": workflow_engine.get_analytics()}


@router.post("/scheduler/start")
async def start_scheduler(authorization: str = Header(None)):
    """Start the workflow scheduler."""
    _user(authorization)
    await workflow_engine.start_scheduler()
    return {"status": "OK", "message": "Scheduler started"}


@router.post("/scheduler/stop")
async def stop_scheduler(authorization: str = Header(None)):
    """Stop the workflow scheduler."""
    _user(authorization)
    await workflow_engine.stop_scheduler()
    return {"status": "OK", "message": "Scheduler stopped"}