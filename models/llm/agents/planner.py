from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable

from models.llm.agents.tools import Tool, ToolResult


@dataclass
class Task:
    id: str
    description: str
    status: str = "pending"
    result: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class Plan:
    goal: str
    tasks: list[Task]
    status: str = "pending"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "tasks": [t.to_dict() for t in self.tasks],
            "status": self.status,
            "metadata": self.metadata,
        }


class Planner(ABC):
    @abstractmethod
    def decompose(self, goal: str, context: dict[str, Any] | None = None) -> Plan:
        raise NotImplementedError

    @abstractmethod
    def execute(self, plan: Plan, tools: dict[str, Tool]) -> Plan:
        raise NotImplementedError

    @abstractmethod
    def replan(self, failed_plan: Plan, failure_info: dict[str, Any], tools: dict[str, Tool]) -> Plan:
        raise NotImplementedError


class SequentialPlanner(Planner):
    def __init__(self, max_retries: int = 3) -> None:
        self.max_retries = max_retries
        self._task_counter = 0

    def _next_id(self) -> str:
        self._task_counter += 1
        return f"task_{self._task_counter}"

    def decompose(self, goal: str, context: dict[str, Any] | None = None) -> Plan:
        self._task_counter = 0
        subtasks = self._generate_subtasks(goal, context or {})
        tasks = [Task(id=self._next_id(), description=desc) for desc in subtasks]
        return Plan(goal=goal, tasks=tasks)

    def _generate_subtasks(self, goal: str, context: dict[str, Any]) -> list[str]:
        segments = [s.strip() for s in goal.replace("\n", ". ").split(".") if s.strip()]
        if len(segments) <= 1:
            return [goal.strip()] if goal.strip() else []
        return segments

    def execute(self, plan: Plan, tools: dict[str, Tool]) -> Plan:
        plan.status = "running"
        for task in plan.tasks:
            task.status = "running"
            tool_name = self._select_tool(task.description, tools)
            tool = tools.get(tool_name)
            if tool is None:
                task.status = "failed"
                task.error = f"No suitable tool found for task: {task.description}"
                continue
            kwargs = self._extract_kwargs(task.description, tool)
            result = tool(**kwargs)
            if result.success:
                task.status = "completed"
                task.result = result.output
            else:
                task.status = "failed"
                task.error = result.error
        if all(t.status == "completed" for t in plan.tasks):
            plan.status = "completed"
        else:
            plan.status = "failed"
        return plan

    def replan(self, failed_plan: Plan, failure_info: dict[str, Any], tools: dict[str, Tool]) -> Plan:
        failed_tasks = [t for t in failed_plan.tasks if t.status == "failed"]
        new_tasks: list[Task] = []
        for task in failed_tasks:
            recovery_desc = f"Recover from failure: {task.error}. Original: {task.description}"
            new_tasks.append(Task(id=self._next_id(), description=recovery_desc, metadata={"recovery": True}))
        plan = Plan(goal=failed_plan.goal, tasks=new_tasks, metadata={"replanned_from": failed_plan.goal})
        return self.execute(plan, tools)

    def _select_tool(self, description: str, tools: dict[str, Tool]) -> str:
        lowered = description.lower()
        for name, tool in tools.items():
            if name.replace("_", " ") in lowered or tool.description.lower() in lowered:
                return name
        return next(iter(tools)) if tools else ""

    def _extract_kwargs(self, description: str, tool: Tool) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}
        schema = tool.to_schema()
        for param_name in schema.get("parameters", {}).get("properties", {}):
            kwargs[param_name] = description
        return kwargs
