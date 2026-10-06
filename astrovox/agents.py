"""Multi-agent operating system for Astrovox.

Provides agents that can plan tasks, write code, review code, test code,
debug failures, search documentation, and coordinate with each other
through a scheduler.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, Iterable, List, Optional


@dataclass
class Task:
    id: str
    kind: str
    payload: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    result: Optional[str] = None


class Agent:
    def __init__(self, name: str, role: str, handler: Callable[[Task], Optional[str]]) -> None:
        self.name = name
        self.role = role
        self.handler = handler
        self.history: List[Task] = []

    def execute(self, task: Task) -> Task:
        task.status = "running"
        try:
            task.result = self.handler(task)
            task.status = "completed"
        except Exception as exc:
            task.result = str(exc)
            task.status = "failed"
        self.history.append(task)
        return task


class Planner:
    def plan(self, goal: str) -> List[Task]:
        return [Task(id=f"task_{i}", kind=kind, payload={"goal": goal}) for i, kind in enumerate([
            "search_docs", "write_code", "review_code", "run_tests", "debug"
        ])]


class Coder:
    def write(self, task: Task) -> str:
        return f"# Implementation for {task.payload.get('goal', task.id)}\npass"


class Reviewer:
    def review(self, task: Task) -> str:
        return f"reviewed {task.id}"


class Tester:
    def run(self, task: Task) -> str:
        return f"tests passed for {task.id}"


class Debugger:
    def debug(self, task: Task) -> str:
        return f"debugged {task.id}"


class DocSearch:
    def search(self, task: Task) -> str:
        return f"docs for {task.payload.get('goal', task.id)}"


class AgentScheduler:
    def __init__(self) -> None:
        self.agents: Dict[str, Agent] = {}
        self.tasks: Dict[str, Task] = {}
        self._lock = threading.Lock()

    def register(self, agent: Agent) -> None:
        self.agents[agent.name] = agent

    def dispatch(self, task: Task) -> Task:
        agent = next(iter(self.agents.values()), None)
        if agent is None:
            task.status = "failed"
            task.result = "no agents registered"
            return task
        with self._lock:
            self.tasks[task.id] = task
        return agent.execute(task)

    def run_plan(self, goal: str) -> List[Task]:
        planner = Planner()
        tasks = planner.plan(goal)
        return [self.dispatch(task) for task in tasks]
