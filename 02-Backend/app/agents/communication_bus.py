"""Agent communication bus."""

from typing import Dict, Any, Optional, List, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import asyncio


class MessageType(Enum):
    REQUEST = "request"
    RESPONSE = "response"
    EVENT = "event"
    COMMAND = "command"
    QUERY = "query"


@dataclass
class AgentMessage:
    message_id: str
    sender_id: str
    recipient_id: str
    message_type: MessageType
    payload: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AgentCommunicationBus:
    _subscribers: Dict[str, List[Callable]] = {}
    _message_queue: asyncio.Queue = asyncio.Queue()
    _running = False

    @classmethod
    def subscribe(cls, agent_id: str, callback: Callable) -> None:
        if agent_id not in cls._subscribers:
            cls._subscribers[agent_id] = []
        cls._subscribers[agent_id].append(callback)

    @classmethod
    async def publish(cls, message: AgentMessage) -> None:
        await cls._message_queue.put(message)
        recipients = cls._subscribers.get(message.recipient_id, [])
        for callback in recipients:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)
            except Exception:
                logger.warning("agent callback failed", exc_info=True)

    @classmethod
    async def send(cls, sender_id: str, recipient_id: str, payload: Dict[str, Any], message_type: MessageType = MessageType.REQUEST) -> AgentMessage:
        message = AgentMessage(
            message_id=f"msg_{datetime.now(timezone.utc).timestamp()}",
            sender_id=sender_id,
            recipient_id=recipient_id,
            message_type=message_type,
            payload=payload,
        )
        await cls.publish(message)
        return message

    @classmethod
    async def broadcast(cls, sender_id: str, payload: Dict[str, Any], message_type: MessageType = MessageType.EVENT) -> List[AgentMessage]:
        messages = []
        for agent_id in cls._subscribers.keys():
            message = AgentMessage(
                message_id=f"msg_{datetime.now(timezone.utc).timestamp()}",
                sender_id=sender_id,
                recipient_id=agent_id,
                message_type=message_type,
                payload=payload,
            )
            await cls.publish(message)
            messages.append(message)
        return messages
