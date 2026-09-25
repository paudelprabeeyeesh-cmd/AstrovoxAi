"""Agents: communication bus and message protocol."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    TASK = "task"
    RESULT = "result"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    DELEGATE = "delegate"


@dataclass
class AgentMessage:
    id: str
    sender: str
    recipient: str
    type: MessageType
    payload: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    correlation_id: Optional[str] = None


class AgentBus:
    """Communication bus for multi-agent systems."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable[[AgentMessage], None]]] = {}
        self._queue: asyncio.Queue = asyncio.Queue()

    def subscribe(self, agent_id: str, handler: Callable[[AgentMessage], None]) -> None:
        self._subscribers.setdefault(agent_id, []).append(handler)

    async def send(self, message: AgentMessage) -> None:
        await self._queue.put(message)

    async def start(self) -> None:
        while True:
            message = await self._queue.get()
            handlers = self._subscribers.get(message.recipient, [])
            for handler in handlers:
                try:
                    handler(message)
                except Exception as exc:
                    logger.error(f"Handler failed for {message.recipient}: {exc}")


_agent_bus: Optional[AgentBus] = None


def get_agent_bus() -> AgentBus:
    global _agent_bus
    if _agent_bus is None:
        _agent_bus = AgentBus()
    return _agent_bus
