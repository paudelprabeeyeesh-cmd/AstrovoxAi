"""Planner agent: decomposes high-level goals into actionable subtasks."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from astrovox.phases._shared.base import BaseAgent

TASK_STATE = ["pending", "running", "completed", "failed"]


@dataclass
class Task:
    """A single decomposed task."""
    id: str
    description: str
    depends_on: list[str] = field(default_factory=list)
    priority: int = 5
    state: str = "pending"
    result: str | None = None

    def to_dict(self) -> dict:
        return {"id": self.id, "description": self.description,
                "depends_on": self.depends_on, "priority": self.priority,
                "state": self.state, "result": self.result}


@dataclass
class Plan:
    """A plan composed of ordered tasks."""
    goal: str
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        self.tasks.append(task)

    def to_dict(self) -> dict:
        return {"goal": self.goal,
                "tasks": [t.to_dict() for t in self.tasks],
                "state": {"pending": 0, "running": 0, "completed": 0, "failed": 0}}


class SequentialPlanner(BaseAgent):
    """A planner that decomposes goals into a sequential task list."""

    def __init__(self, name: str = "planner", max_tasks: int = 50):
        super().__init__(name, role="planner")
        self.max_tasks = max_tasks
        self.plans: list[Plan] = []
        self._task_counter = 0

    def plan(self, goal: str) -> Plan:
        """Decompose a goal into sequential tasks."""
        self._task_counter += 1
        plan = Plan(goal=goal)
        for i, part in enumerate(goal.split(" | ")):
            if len(plan.tasks) >= self.max_tasks:
                break
            task = Task(id=f"{self._task_counter}-{i}",
                        description=part.strip(), depends_on=[] if i == 0 else [plan.tasks[-1].id])
            plan.add_task(task)
        if not plan.tasks:
            plan.add_task(Task(id=f"{self._task_counter}-0", description=goal, depends_on=[]))
        self.plans.append(plan)
        return plan

    def execute(self, plan: Plan) -> Plan:
        """Execute tasks in plan order."""
        for task in plan.tasks:
            task.state = "running"
            task.result = self.run_task(task.description)
            task.state = "completed"
        return plan

    def decompose(self, goal: str, strategy: str = "sequential") -> Plan:
        """Decompose a goal into a plan using the given strategy."""
        if strategy == "sequential":
            return self.plan(goal)
        raise ValueError(f"Unknown strategy: {strategy}")

    def replan(self, plan: Plan, reason: str) -> Plan:
        """Replan after a failure or changed observation."""
        return self.decompose(f"{plan.goal} (retry after: {reason})")

    def run_task(self, description: str) -> str:
        """Execute a single task description."""
        return f"executed: {description}"
