"""Shared base classes for Astrovox phase modules."""

from __future__ import annotations

import abc
import json
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentMessage:
    """A message between agents or agent and environment."""
    sender: str
    receiver: str
    content: str
    msg_type: str = "text"
    timestamp: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"sender": self.sender, "receiver": self.receiver,
                "content": self.content, "msg_type": self.msg_type,
                "timestamp": self.timestamp, "metadata": self.metadata}

    @classmethod
    def from_dict(cls, d: dict) -> "AgentMessage":
        return cls(**d)


class BaseAgent(abc.ABC):
    """Abstract base for phase agents."""

    def __init__(self, name: str, role: str = "general"):
        self.name = name
        self.role = role

    @abc.abstractmethod
    def plan(self, observation: Any) -> dict:
        """Decide the next action."""

    @abc.abstractmethod
    def act(self, action: dict) -> Any:
        """Execute an action."""


class BaseStore(abc.ABC):
    """Abstract base for phase memory stores."""

    @abc.abstractmethod
    def set(self, key: str, value: Any) -> None:
        """Store a value."""

    @abc.abstractmethod
    def get(self, key: str) -> Any | None:
        """Retrieve a value."""

    @abc.abstractmethod
    def search(self, query: str, limit: int = 20) -> list[dict]:
        """Search the store."""
