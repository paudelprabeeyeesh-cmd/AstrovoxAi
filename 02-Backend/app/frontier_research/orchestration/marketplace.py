"""Multi-agent orchestration and marketplace stubs."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AgentManifest:
    agent_id: str
    name: str
    capabilities: list[str]
    endpoint: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    task_id: str
    description: str
    required_capabilities: list[str]
    payload: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"


@dataclass
class AgentResult:
    agent_id: str
    task_id: str
    output: Any
    latency_ms: float = 0.0
    error: str | None = None


class AgentMarketplace:
    def __init__(self):
        self.agents: dict[str, AgentManifest] = {}

    def register(self, manifest: AgentManifest) -> None:
        self.agents[manifest.agent_id] = manifest

    def discover(self, capabilities: list[str]) -> list[AgentManifest]:
        return [agent for agent in self.agents.values() if all(cap in agent.capabilities for cap in capabilities)]

    def unregister(self, agent_id: str) -> None:
        self.agents.pop(agent_id, None)


class Orchestrator:
    def __init__(self, marketplace: AgentMarketplace | None = None):
        self.marketplace = marketplace or AgentMarketplace()
        self.tasks: dict[str, Task] = {}

    def submit(self, task: Task) -> list[AgentResult]:
        self.tasks[task.task_id] = task
        candidates = self.marketplace.discover(task.required_capabilities)
        if not candidates:
            return [AgentResult(agent_id="none", task_id=task.task_id, output=None, error="no agents found")]
        results: list[AgentResult] = []
        for candidate in candidates[:3]:
            result = self._dispatch(candidate, task)
            results.append(result)
        return results

    def _dispatch(self, agent: AgentManifest, task: Task) -> AgentResult:
        start = time.perf_counter()
        try:
            output = self._call_agent(agent, task)
            latency = (time.perf_counter() - start) * 1000
            return AgentResult(agent_id=agent.agent_id, task_id=task.task_id, output=output, latency_ms=latency)
        except Exception as exc:
            logger.error("Dispatch to %s failed: %s", agent.agent_id, exc)
            return AgentResult(agent_id=agent.agent_id, task_id=task.task_id, output=None, error=str(exc))

    def _call_agent(self, agent: AgentManifest, task: Task) -> Any:
        if agent.endpoint:
            import httpx
            with httpx.Client(timeout=30) as client:
                response = client.post(agent.endpoint, json={"task_id": task.task_id, "payload": task.payload})
                response.raise_for_status()
                return response.json()
        return {"agent_id": agent.agent_id, "task_id": task.task_id, "status": "simulated"}
