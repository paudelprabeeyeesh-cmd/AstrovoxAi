"""Core agent framework: base Agent class, registry, and lifecycle management.

An Astrovox agent is a stateful, tool-equipped entity that observes state,
decides actions via its reasoning policy, and acts through tools. Agents are
registered in a global registry and coordinated by teams/schedulers.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine, Optional


class AgentRole(Enum):
    """Standard agent roles used across the Astrovox system."""
    PLANNER = "planner"
    CODER = "coder"
    RESEARCHER = "researcher"
    TESTER = "tester"
    DEBUGGER = "debugger"
    OPERATOR = "operator"
    GENERAL = "general"


class AgentStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    COMPLETED = "completed"


@dataclass
class AgentConfig:
    """Configuration for an agent instance."""
    name: str
    role: AgentRole = AgentRole.GENERAL
    system_prompt: str = ""
    tools: list = field(default_factory=list)
    max_steps: int = 100
    working_dir: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class AgentMessage:
    """A message between agents or between agent and environment."""
    sender: str
    receiver: str
    content: str
    msg_type: str = "text"
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"sender": self.sender, "receiver": self.receiver,
                "content": self.content, "msg_type": self.msg_type,
                "timestamp": self.timestamp, "metadata": self.metadata}

    @classmethod
    def from_dict(cls, d: dict) -> "AgentMessage":
        return cls(**d)


class Agent(ABC):
    """Abstract base class for all Astrovox agents.

    Subclasses implement :meth:`plan` to decide what to do next and
    :meth:`act` to execute the chosen action. The base class handles lifecycle,
    observation, message handling, and persistence.
    """

    def __init__(self, config: AgentConfig):
        self.id = str(uuid.uuid4())[:8]
        self.name = config.name
        self.role = config.role
        self.system_prompt = config.system_prompt
        self.tools = {t.name: t for t in config.tools}
        self.max_steps = config.max_steps
        self.working_dir = config.working_dir
        self.metadata = config.metadata.copy()
        self.status = AgentStatus.IDLE
        self.observation: Any = None
        self.history: list[AgentMessage] = []
        self.result: Any = None
        self.error: Optional[str] = None
        self.steps = 0
        self._running = False

    @abstractmethod
    def plan(self, observation: Any) -> dict:
        """Decide the next action given the current observation."""

    @abstractmethod
    def act(self, action: dict) -> Any:
        """Execute an action and return the result."""

    def observe(self, observation: Any) -> None:
        self.observation = observation
        self.steps += 1

    def send(self, receiver: str, content: str, msg_type: str = "text",
             metadata: dict | None = None) -> AgentMessage:
        msg = AgentMessage(self.id, receiver, content, msg_type, metadata=metadata or {})
        self.history.append(msg)
        return msg

    def receive(self, msg: AgentMessage) -> None:
        self.history.append(msg)

    def step(self) -> Any:
        """Run a single plan-act cycle."""
        if self.status != AgentStatus.RUNNING:
            raise RuntimeError("Agent is not running")
        action = self.plan(self.observation)
        self.result = self.act(action)
        return self.result

    def run(self, observation: Any, max_steps: int | None = None) -> Any:
        """Run the agent until completion or max steps."""
        self.status = AgentStatus.RUNNING
        self._running = True
        max_steps = max_steps or self.max_steps
        try:
            self.observe(observation)
            for _ in range(max_steps):
                if self._should_stop():
                    break
                self.step()
        except Exception as e:
            self.error = str(e)
            self.status = AgentStatus.ERROR
        finally:
            self.status = AgentStatus.COMPLETED if self.error is None else AgentStatus.ERROR
            self._running = False
        return self.result

    def _should_stop(self) -> bool:
        if self.steps >= self.max_steps:
            return True
        return False

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "role": self.role.value,
                "status": self.status.value, "steps": self.steps,
                "result": str(self.result), "error": self.error}


class AgentRegistry:
    """Global registry for agent classes and named instances."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._agents = {}
            cls._instance._factories = {}
        return cls._instance

    def register_factory(self, role: AgentRole, factory: Callable[[AgentConfig], Agent]) -> None:
        self._factories[role] = factory

    def create(self, role: AgentRole, config: AgentConfig) -> Agent:
        if role not in self._factories:
            raise KeyError(f"No factory registered for role {role}")
        agent = self._factories[role](config)
        self._agents[agent.id] = agent
        return agent

    def get(self, agent_id: str) -> Agent | None:
        return self._agents.get(agent_id)

    def list_agents(self) -> list[Agent]:
        return list(self._agents.values())

    def remove(self, agent_id: str) -> bool:
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False

    def clear(self) -> None:
        self._agents.clear()


def get_registry() -> AgentRegistry:
    return AgentRegistry()
