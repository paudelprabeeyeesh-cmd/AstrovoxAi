"""Autonomous agent runtime.

Each agent has a lifecycle, working memory, tool permissions, planning,
and collaboration primitives that operate over the kernel event bus.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional

from .bus import get_event_bus


class AgentState(str, Enum):
    IDLE = "idle"
    PLANNING = "planning"
    RUNNING = "running"
    WAITING = "waiting"
    REFLECTING = "reflecting"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class AgentMessage:
    """Structured inter-agent message."""

    id: str
    sender: str
    recipient: str
    topic: str
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sender": self.sender,
            "recipient": self.recipient,
            "topic": self.topic,
            "payload": self.payload,
            "created_at": self.created_at,
            "correlation_id": self.correlation_id,
        }


@dataclass
class AgentSpec:
    name: str
    role: str
    description: str = ""
    tools: List[str] = field(default_factory=list)
    resource_limit: Dict[str, float] = field(default_factory=dict)
    max_iterations: int = 5


@dataclass
class WorkingMemory:
    scratchpad: List[Dict[str, Any]] = field(default_factory=list)
    facts: Dict[str, Any] = field(default_factory=dict)
    history: deque[Any] = field(default_factory=lambda: deque(maxlen=200))

    def remember(self, key: str, value: Any) -> None:
        self.facts[key] = value
        self.history.append({"type": "fact", "key": key, "value": value, "ts": time.time()})

    def note(self, content: str) -> None:
        self.scratchpad.append({"content": content, "ts": time.time()})
        self.history.append({"type": "note", "content": content, "ts": time.time()})

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scratchpad": list(self.scratchpad),
            "facts": dict(self.facts),
            "history": list(self.history)[-20:],
        }


class Agent:
    """Autonomous agent with planning, reflection, and collaboration."""

    def __init__(self, spec: AgentSpec) -> None:
        self.spec = spec
        self.id = f"agent_{uuid.uuid4().hex[:10]}"
        self.state = AgentState.IDLE
        self.memory = WorkingMemory()
        self.inbox: deque[AgentMessage] = deque(maxlen=200)
        self.iteration = 0
        self.health: Dict[str, Any] = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "last_active": None,
        }
        self._bus = get_event_bus()
        self._lock = asyncio.Lock()
        self._tool_executor: Optional[Callable[[str, Dict[str, Any]], Awaitable[Any]]] = None
        self._register_subscriptions()

    # ----- messaging ---------------------------------------------------

    def _register_subscriptions(self) -> None:
        topic = f"agent.{self.spec.name}.inbox"
        self._bus.subscribe(topic, self._receive_event)

    def _receive_event(self, event: Any) -> None:
        msg = AgentMessage(
            id=event.id,
            sender=event.payload.get("sender", event.source),
            recipient=self.spec.name,
            topic=event.payload.get("topic", "message"),
            payload=event.payload,
            correlation_id=event.correlation_id,
        )
        self.inbox.append(msg)

    async def send(
        self,
        recipient: str,
        topic: str,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> None:
        self._bus.publish(
            f"agent.{recipient}.inbox",
            {"sender": self.spec.name, "topic": topic, "payload": payload},
            source=self.spec.name,
            correlation_id=correlation_id,
        )

    # ----- tools -------------------------------------------------------

    def set_tool_executor(
        self, executor: Callable[[str, Dict[str, Any]], Awaitable[Any]]
    ) -> None:
        self._tool_executor = executor

    async def call_tool(self, name: str, args: Dict[str, Any]) -> Any:
        if name not in self.spec.tools:
            raise PermissionError(f"agent {self.spec.name} cannot call tool {name}")
        if not self._tool_executor:
            return {"ok": True, "echo": args}
        result = await self._tool_executor(name, args)
        self.memory.history.append(
            {"type": "tool", "tool": name, "args": args, "result": result, "ts": time.time()}
        )
        return result

    # ----- planning ----------------------------------------------------

    def plan(self, goal: str) -> List[Dict[str, Any]]:
        # Heuristic plan: a small list of subtasks with explicit tool/agent
        # annotations.  A real implementation calls the LLM.
        plan = [
            {"step": "gather", "description": f"Gather context for {goal}", "tools": []},
            {"step": "execute", "description": f"Execute primary action for {goal}", "tools": []},
            {"step": "verify", "description": f"Verify outcome of {goal}", "tools": []},
            {"step": "reflect", "description": f"Reflect on {goal} results", "tools": []},
        ]
        self.memory.note(f"planned: {plan}")
        return plan

    def reflect(self) -> Dict[str, Any]:
        recent = list(self.memory.history)[-10:]
        successes = sum(1 for h in recent if h.get("type") == "tool")
        failures = sum(1 for h in recent if h.get("type") == "tool" and h.get("result", {}).get("error"))
        return {"successes": successes, "failures": failures, "recent": len(recent)}

    # ----- lifecycle ---------------------------------------------------

    async def run(self, goal: str) -> Dict[str, Any]:
        async with self._lock:
            self.iteration = 0
            self.state = AgentState.PLANNING
            plan = self.plan(goal)
            self.state = AgentState.RUNNING
            results: List[Dict[str, Any]] = []
            while self.iteration < self.spec.max_iterations and plan:
                step = plan.pop(0)
                self.iteration += 1
                self.memory.note(f"executing step: {step['step']}")
                # Minimal execution: record a result. Real impl dispatches to tools.
                result = {"step": step["step"], "ok": True, "ts": time.time()}
                results.append(result)
                self._bus.publish(
                    "agent.step",
                    {"agent": self.spec.name, "step": step["step"]},
                    source=self.spec.name,
                )
            self.state = AgentState.REFLECTING
            reflection = self.reflect()
            self.state = AgentState.IDLE
            self.health["tasks_completed"] += 1
            self.health["last_active"] = datetime.now(timezone.utc).isoformat()
            self._bus.publish(
                "agent.finished",
                {
                    "agent": self.spec.name,
                    "goal": goal,
                    "iterations": self.iteration,
                    "results": results,
                    "reflection": reflection,
                },
                source=self.spec.name,
            )
            return {
                "agent": self.spec.name,
                "goal": goal,
                "iterations": self.iteration,
                "results": results,
                "reflection": reflection,
            }

    def stop(self) -> None:
        self.state = AgentState.STOPPED
        self._bus.publish("agent.stopped", {"agent": self.spec.name}, source=self.spec.name)


class AgentRegistry:
    """Tracks running agents and supports discovery."""

    def __init__(self) -> None:
        self._agents: Dict[str, Agent] = {}

    def register(self, agent: Agent) -> Agent:
        self._agents[agent.id] = agent
        get_event_bus().publish("agent.registered", {"id": agent.id, "name": agent.spec.name})
        return agent

    def unregister(self, agent_id: str) -> Optional[Agent]:
        return self._agents.pop(agent_id, None)

    def get(self, agent_id: str) -> Optional[Agent]:
        return self._agents.get(agent_id)

    def by_name(self, name: str) -> List[Agent]:
        return [a for a in self._agents.values() if a.spec.name == name]

    def list(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": a.id,
                "name": a.spec.name,
                "role": a.spec.role,
                "state": a.state.value,
                "iteration": a.iteration,
                "tools": a.spec.tools,
                "health": a.health,
            }
            for a in self._agents.values()
        ]


_GLOBAL_REGISTRY: Optional[AgentRegistry] = None


def get_agent_registry() -> AgentRegistry:
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        _GLOBAL_REGISTRY = AgentRegistry()
    return _GLOBAL_REGISTRY