"""Planner agent for task decomposition."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class PlanStatus(Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskStep:
    step_id: str
    description: str
    status: PlanStatus = PlanStatus.DRAFT
    dependencies: List[str] = field(default_factory=list)
    estimated_tokens: int = 0
    assigned_agent: Optional[str] = None
    result: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Plan:
    plan_id: str
    user_id: str
    goal: str
    steps: List[TaskStep]
    status: PlanStatus = PlanStatus.DRAFT
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


class PlannerAgent:
    _plans: Dict[str, Plan] = {}

    @classmethod
    def create_plan(cls, user_id: str, goal: str) -> Plan:
        plan_id = f"plan_{user_id}_{len(cls._plans)}"
        plan = Plan(plan_id=plan_id, user_id=user_id, goal=goal, steps=[])
        cls._plans[plan_id] = plan
        return plan

    @classmethod
    def add_step(cls, plan_id: str, step: TaskStep) -> None:
        plan = cls._plans.get(plan_id)
        if plan:
            plan.steps.append(step)

    @classmethod
    def get_plan(cls, plan_id: str) -> Optional[Plan]:
        return cls._plans.get(plan_id)

    @classmethod
    def update_step_status(cls, plan_id: str, step_id: str, status: PlanStatus) -> None:
        plan = cls._plans.get(plan_id)
        if plan:
            for step in plan.steps:
                if step.step_id == step_id:
                    step.status = status
                    break
