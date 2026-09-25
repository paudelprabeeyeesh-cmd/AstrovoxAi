"""Next-gen distributed coordinator with capability-based task dispatch."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AgentTask:
    task_id: str
    agent_type: str
    payload: Dict[str, Any]
    priority: int = 0
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"
    result: Optional[Any] = None
    created_at: float = field(default_factory=time.time)


class NextGenDistributedCoordinator:
    def __init__(self, coordinator_id: str):
        self.coordinator_id = coordinator_id
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.task_queue: deque = deque()
        self.in_flight: Dict[str, AgentTask] = {}
        self.completed: List[AgentTask] = []
        self.capability_index: Dict[str, List[str]] = {}
        self.lock = asyncio.Lock()

    def register_agent(self, agent_id: str, capabilities: List[str], endpoint: str) -> None:
        self.agents[agent_id] = {"capabilities": capabilities, "endpoint": endpoint, "load": 0.0}
        for cap in capabilities:
            self.capability_index.setdefault(cap, []).append(agent_id)

    def submit_task(self, task: AgentTask) -> str:
        self.task_queue.append(task)
        return task.task_id

    def dispatch(self) -> List[AgentTask]:
        dispatched = []
        ready = [t for t in self.task_queue if all(d in [c.task_id for c in self.completed] for d in t.dependencies)]
        for task in ready:
            candidates = self.capability_index.get(task.agent_type, [])
            if not candidates:
                continue
            agent_id = min(candidates, key=lambda aid: self.agents[aid]["load"])
            task.status = "assigned"
            self.in_flight[task.task_id] = task
            self.agents[agent_id]["load"] += 1
            dispatched.append(task)
            self.task_queue.remove(task)
        return dispatched

    def complete_task(self, task_id: str, result: Any) -> None:
        task = self.in_flight.pop(task_id, None)
        if task:
            task.status = "completed"
            task.result = result
            self.completed.append(task)
            for agent in self.agents.values():
                if agent["load"] > 0:
                    agent["load"] -= 1

    def fail_task(self, task_id: str, reason: str) -> None:
        task = self.in_flight.pop(task_id, None)
        if task:
            task.status = "failed"
            self.completed.append(task)

    def rebalance(self) -> Dict[str, Any]:
        loads = {aid: info["load"] for aid, info in self.agents.items()}
        avg = sum(loads.values()) / max(len(loads), 1)
        overloaded = [aid for aid, load in loads.items() if load > avg * 1.5]
        underloaded = [aid for aid, load in loads.items() if load < avg * 0.5]
        return {"overloaded": overloaded, "underloaded": underloaded, "average_load": avg}
