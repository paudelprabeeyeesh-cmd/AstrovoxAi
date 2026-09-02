"""Distributed AI runtime: agent isolation, quotas, message routing, delegation."""

from __future__ import annotations

import asyncio
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Awaitable, Callable, Deque, Dict, List, Optional, Set, Tuple

from . import make_id, now
from ..kernel.agents import Agent, AgentSpec, AgentRegistry
from ..kernel.bus import get_event_bus


class QuotaUsage(str, Enum):
    OK = "ok"
    WARNING = "warning"
    EXCEEDED = "exceeded"


@dataclass
class AgentQuota:
    name: str
    max_concurrent: int = 4
    max_tasks_per_minute: int = 120
    max_tokens_per_minute: int = 200_000
    used_concurrent: int = 0
    used_tasks: int = 0
    used_tokens: int = 0
    window_started_at: float = field(default_factory=now)

    def acquire(self, tokens: int = 0) -> QuotaUsage:
        self._reset_window()
        if self.used_concurrent >= self.max_concurrent:
            return QuotaUsage.EXCEEDED
        if self.used_tasks >= self.max_tasks_per_minute:
            return QuotaUsage.EXCEEDED
        if self.used_tokens + tokens > self.max_tokens_per_minute:
            return QuotaUsage.EXCEEDED
        self.used_concurrent += 1
        self.used_tasks += 1
        self.used_tokens += tokens
        if self.used_tasks >= self.max_tasks_per_minute * 0.8:
            return QuotaUsage.WARNING
        return QuotaUsage.OK

    def release(self, tokens: int = 0) -> None:
        self.used_concurrent = max(0, self.used_concurrent - 1)
        self.used_tokens = max(0, self.used_tokens - tokens)

    def _reset_window(self) -> None:
        if now() - self.window_started_at > 60:
            self.used_tasks = 0
            self.used_tokens = 0
            self.window_started_at = now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "max_concurrent": self.max_concurrent,
            "max_tasks_per_minute": self.max_tasks_per_minute,
            "max_tokens_per_minute": self.max_tokens_per_minute,
            "used_concurrent": self.used_concurrent,
            "used_tasks": self.used_tasks,
            "used_tokens": self.used_tokens,
        }


@dataclass
class Message:
    id: str
    sender: str
    recipient: str
    topic: str
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=now)
    delivered: bool = False
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sender": self.sender,
            "recipient": self.recipient,
            "topic": self.topic,
            "payload": self.payload,
            "created_at": self.created_at,
            "delivered": self.delivered,
            "correlation_id": self.correlation_id,
        }


class MessageRouter:
    """Routes messages between agents with optional broadcast."""

    def __init__(self) -> None:
        self._inboxes: Dict[str, Deque[Message]] = defaultdict(lambda: deque(maxlen=1000))
        self._routes: Dict[str, List[str]] = defaultdict(list)
        self._log: List[Message] = []

    def register(self, agent_name: str) -> None:
        self._inboxes.setdefault(agent_name, deque(maxlen=1000))

    def route(self, topic: str, agent_names: Iterable[str]) -> None:
        self._routes[topic].extend(agent_names)

    def send(
        self,
        sender: str,
        recipient: str,
        topic: str,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> Message:
        msg = Message(
            id=make_id("msg"),
            sender=sender,
            recipient=recipient,
            topic=topic,
            payload=payload,
            correlation_id=correlation_id,
        )
        self._inboxes[recipient].append(msg)
        self._log.append(msg)
        if len(self._log) > 2000:
            self._log = self._log[-2000:]
        return msg

    def broadcast(self, sender: str, topic: str, payload: Dict[str, Any]) -> List[Message]:
        sent: List[Message] = []
        for agent_name in list(self._inboxes.keys()):
            sent.append(self.send(sender, agent_name, topic, payload))
        return sent

    def inbox(self, agent_name: str) -> List[Message]:
        return list(self._inboxes.get(agent_name, deque()))

    def drain(self, agent_name: str) -> List[Message]:
        items = list(self._inboxes.get(agent_name, deque()))
        self._inboxes[agent_name].clear()
        return items

    def history(self, limit: int = 100) -> List[Dict[str, Any]]:
        return [m.to_dict() for m in self._log[-limit:]]


@dataclass
class DelegationRequest:
    """A request to delegate work from one agent to another."""

    id: str
    from_agent: str
    to_agent: str
    goal: str
    context: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    state: str = "pending"
    created_at: float = field(default_factory=now)
    finished_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "goal": self.goal,
            "context": self.context,
            "result": self.result,
            "error": self.error,
            "state": self.state,
            "created_at": self.created_at,
            "finished_at": self.finished_at,
        }


class AIRuntime:
    """Coordinates many agents with isolation, quotas, and delegation."""

    def __init__(self, registry: Optional[AgentRegistry] = None) -> None:
        self.registry = registry or AgentRegistry()
        self.router = MessageRouter()
        self.quotas: Dict[str, AgentQuota] = {}
        self.delegations: Dict[str, DelegationRequest] = {}

    # ---- agent management ------------------------------------------

    def register_agent(
        self,
        name: str,
        role: str,
        *,
        max_concurrent: int = 4,
        max_tasks_per_minute: int = 120,
        max_tokens_per_minute: int = 200_000,
        tools: Optional[List[str]] = None,
    ) -> Agent:
        spec = AgentSpec(
            name=name,
            role=role,
            tools=tools or [],
            max_iterations=4,
        )
        agent = Agent(spec)
        self.registry.register(agent)
        self.router.register(name)
        self.quotas[name] = AgentQuota(
            name=name,
            max_concurrent=max_concurrent,
            max_tasks_per_minute=max_tasks_per_minute,
            max_tokens_per_minute=max_tokens_per_minute,
        )
        get_event_bus().publish(
            "aios.agent.registered",
            {"id": agent.id, "name": name, "role": role},
            source="aios.runtime",
        )
        return agent

    # ---- execution --------------------------------------------------

    async def run_agent(self, name: str, goal: str, *, tokens: int = 0) -> Dict[str, Any]:
        quota = self.quotas.get(name)
        if quota is None:
            return {"ok": False, "error": f"unknown agent: {name}"}
        status = quota.acquire(tokens=tokens)
        if status == QuotaUsage.EXCEEDED:
            return {"ok": False, "error": "quota exceeded", "agent": name}
        agent = next((a for a in self.registry.by_name(name)), None)
        if agent is None:
            quota.release(tokens=tokens)
            return {"ok": False, "error": f"agent not registered: {name}"}
        try:
            result = await agent.run(goal)
            return {"ok": True, "agent": name, "result": result, "quota": quota.to_dict()}
        finally:
            quota.release(tokens=tokens)

    # ---- messaging --------------------------------------------------

    def send(self, sender: str, recipient: str, topic: str, payload: Dict[str, Any]) -> Message:
        return self.router.send(sender, recipient, topic, payload)

    def broadcast(self, sender: str, topic: str, payload: Dict[str, Any]) -> List[Message]:
        return self.router.broadcast(sender, topic, payload)

    def inbox(self, agent_name: str) -> List[Dict[str, Any]]:
        return [m.to_dict() for m in self.router.inbox(agent_name)]

    # ---- delegation -------------------------------------------------

    async def delegate(
        self,
        from_agent: str,
        to_agent: str,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> DelegationRequest:
        req = DelegationRequest(
            id=make_id("del"),
            from_agent=from_agent,
            to_agent=to_agent,
            goal=goal,
            context=context or {},
        )
        self.delegations[req.id] = req
        result = await self.run_agent(to_agent, goal)
        req.finished_at = now()
        if result.get("ok"):
            req.result = result.get("result")
            req.state = "succeeded"
        else:
            req.error = result.get("error", "unknown")
            req.state = "failed"
        return req

    # ---- status -----------------------------------------------------

    def status(self) -> Dict[str, Any]:
        return {
            "agents": self.registry.list(),
            "quotas": {name: q.to_dict() for name, q in self.quotas.items()},
            "delegations": [d.to_dict() for d in self.delegations.values()],
            "messages": len(self.router._log),
        }


_GLOBAL_RUNTIME: Optional[AIRuntime] = None


def get_ai_runtime() -> AIRuntime:
    global _GLOBAL_RUNTIME
    if _GLOBAL_RUNTIME is None:
        _GLOBAL_RUNTIME = AIRuntime()
    return _GLOBAL_RUNTIME