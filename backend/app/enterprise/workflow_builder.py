"""Workflow builder — visual automation with triggers, steps, and actions."""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class WorkflowStep:
    id: str
    name: str
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    condition: Optional[Dict[str, Any]] = None
    next_on_success: Optional[str] = None
    next_on_failure: Optional[str] = None


@dataclass
class WorkflowTrigger:
    id: str
    type: str
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Workflow:
    id: str
    name: str
    org_id: str
    trigger: WorkflowTrigger
    steps: List[WorkflowStep] = field(default_factory=list)
    is_active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class WorkflowBuilder:
    def __init__(self):
        self._workflows: Dict[str, Workflow] = {}
        self._actions: Dict[str, Callable] = {}

    def register_action(self, name: str, handler: Callable) -> None:
        self._actions[name] = handler
        logger.debug("Registered workflow action %s", name)

    def create_workflow(self, name: str, org_id: str, trigger_type: str, trigger_config: Dict[str, Any] = None) -> Workflow:
        workflow_id = str(uuid.uuid4())
        trigger = WorkflowTrigger(id=f"trigger_{workflow_id[:8]}", type=trigger_type, config=trigger_config or {})
        workflow = Workflow(id=workflow_id, name=name, org_id=org_id, trigger=trigger)
        self._workflows[workflow_id] = workflow
        logger.info("Created workflow %s for org %s", workflow_id, org_id)
        return workflow

    def add_step(self, workflow_id: str, name: str, action: str, params: Dict[str, Any] = None, condition: Optional[Dict[str, Any]] = None, next_on_success: Optional[str] = None, next_on_failure: Optional[str] = None) -> WorkflowStep:
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        step_id = str(uuid.uuid4())
        step = WorkflowStep(id=step_id, name=name, action=action, params=params or {}, condition=condition, next_on_success=next_on_success, next_on_failure=next_on_failure)
        workflow.steps.append(step)
        logger.debug("Added step %s to workflow %s", step_id, workflow_id)
        return step

    def execute(self, workflow_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
        workflow = self._workflows.get(workflow_id)
        if not workflow or not workflow.is_active:
            raise ValueError(f"Workflow {workflow_id} not found or inactive")
        logger.info("Executing workflow %s", workflow_id)
        current_step = None
        for step in workflow.steps:
            if step.condition and not self._evaluate_condition(step.condition, event):
                continue
            handler = self._actions.get(step.action)
            if not handler:
                logger.warning("Action %s not registered for step %s", step.action, step.id)
                continue
            try:
                result = handler(**step.params, event=event)
                current_step = step.id
                event["last_result"] = result
            except Exception as exc:
                logger.error("Step %s failed: %s", step.id, exc)
                if step.next_on_failure:
                    continue
                break
        return {"workflow_id": workflow_id, "last_step": current_step, "event": event}

    def _evaluate_condition(self, condition: Dict[str, Any], event: Dict[str, Any]) -> bool:
        for key, value in condition.items():
            if key not in event or event[key] != value:
                return False
        return True

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        return self._workflows.get(workflow_id)

    def list_workflows(self, org_id: str) -> List[dict]:
        return [
            {
                "id": w.id,
                "name": w.name,
                "org_id": w.org_id,
                "trigger_type": w.trigger.type,
                "is_active": w.is_active,
                "steps_count": len(w.steps),
                "created_at": w.created_at,
            }
            for w in self._workflows.values()
            if w.org_id == org_id
        ]


workflow_builder = WorkflowBuilder()
