"""Agent communication: message passing, queues, and broadcast."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable
from collections import deque


@dataclass
class Message:
    """A message on the agent communication bus."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    sender: str = ""
    receiver: str = ""
    payload: Any = None
    msg_type: str = "text"
    timestamp: float = field(default_factory=lambda: asyncio.get_event_loop().time() if hasattr(asyncio, 'get_event_loop') else __import__('time').time())

    def to_dict(self) -> dict:
        return {"id": self.id, "sender": self.sender, "receiver": self.receiver,
                "payload": self.payload, "msg_type": self.msg_type,
                "timestamp": self.timestamp}


class MessageQueue:
    """Async message queue for agent communication."""

    def __init__(self, name: str = "default", capacity: int = 1000):
        self.name = name
        self.capacity = capacity
        self._queue: deque = deque()
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Condition(self._lock)
        self.handlers: dict[str, Callable[[Message], Any]] = {}
        self.delivery_count = 0

    async def put(self, msg: Message) -> bool:
        async with self._not_empty:
            if len(self._queue) >= self.capacity:
                self._queue.popleft()
            self._queue.append(msg)
            self._not_empty.notify()
            return True

    async def get(self, timeout: float | None = None) -> Message | None:
        async with self._not_empty:
            while not self._queue:
                try:
                    await asyncio.wait_for(self._not_empty.wait(), timeout=timeout)
                except asyncio.TimeoutError:
                    return None
            msg = self._queue.popleft()
            self.delivery_count += 1
            return msg

    def register(self, name: str, handler: Callable[[Message], Any]) -> None:
        self.handlers[name] = handler

    async def dispatch(self, msg: Message) -> Any:
        name = msg.msg_type
        handler = self.handlers.get(name)
        if handler is not None:
            return handler(msg)
        return None

    def __len__(self) -> int:
        return len(self._queue)


class AgentBus:
    """Message bus connecting agents."""

    def __init__(self):
        self.queues: dict[str, MessageQueue] = {}
        self.subscribers: dict[str, set[str]] = {}  # topic -> agent ids

    def create_queue(self, name: str, capacity: int = 1000) -> MessageQueue:
        self.queues[name] = MessageQueue(name=name, capacity=capacity)
        return self.queues[name]

    def send(self, to: str, payload: Any, msg_type: str = "text") -> Message:
        msg = Message(sender="__system__", receiver=to, payload=payload, msg_type=msg_type)
        queue = self.queues.get(to)
        if queue is not None:
            asyncio.create_task(queue.put(msg))
        return msg

    def broadcast(self, topic: str, payload: Any, msg_type: str = "broadcast") -> None:
        agents = self.subscribers.get(topic, set())
        for agent_id in agents:
            self.send(agent_id, payload, msg_type)

    def subscribe(self, topic: str, agent_id: str) -> None:
        self.subscribers.setdefault(topic, set()).add(agent_id)

    def unsubscribe(self, topic: str, agent_id: str) -> None:
        agents = self.subscribers.get(topic, set())
        agents.discard(agent_id)


def create_bus() -> AgentBus:
    return AgentBus()
