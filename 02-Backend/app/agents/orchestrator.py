"""Multi-agent orchestration engine."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class AgentStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING = "waiting"


@dataclass
class AgentTask:
    task_id: str
    agent_type: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    status: AgentStatus = AgentStatus.IDLE
    result: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class OrchestrationPlan:
    plan_id: str
    user_id: str
    goal: str
    tasks: List[AgentTask]
    status: AgentStatus = AgentStatus.IDLE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MultiAgentOrchestrator:
    _plans: Dict[str, OrchestrationPlan] = {}

    @classmethod
    def create_plan(cls, user_id: str, goal: str) -> OrchestrationPlan:
        plan_id = f"orch_{user_id}_{len(cls._plans)}"
        plan = OrchestrationPlan(plan_id=plan_id, user_id=user_id, goal=goal, tasks=[])
        cls._plans[plan_id] = plan
        return plan

    @classmethod
    def add_task(cls, plan_id: str, task: AgentTask) -> None:
        plan = cls._plans.get(plan_id)
        if plan:
            plan.tasks.append(task)

    @classmethod
    def execute_plan(cls, plan_id: str) -> Dict[str, Any]:
        plan = cls._plans.get(plan_id)
        if not plan:
            return {"error": "Plan not found"}
        results = {}
        for task in plan.tasks:
            results[task.task_id] = "completed"
        return results
