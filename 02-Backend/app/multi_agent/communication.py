"""Agent communication protocols."""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Message:
    id: str
    from_agent: str
    to_agent: str
    content: str
    channel: str = "default"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict = field(default_factory=dict)


@dataclass
class Channel:
    name: str
    subscribers: list[str] = field(default_factory=list)
    history: list[Message] = field(default_factory=list)


class AgentCommunicator:
    def __init__(self):
        self._channels: dict[str, Channel] = {}
        self._inboxes: dict[str, list[Message]] = {}

    def create_channel(self, name: str, subscribers: Optional[list[str]] = None) -> Channel:
        channel = Channel(name=name, subscribers=subscribers or [])
        self._channels[name] = channel
        return channel

    def send_message(self, from_agent: str, to_agent: str, content: str, channel: str = "default") -> Message:
        message = Message(id=str(uuid.uuid4()), from_agent=from_agent, to_agent=to_agent, content=content, channel=channel)
        ch = self._channels.setdefault(channel, Channel(name=channel))
        ch.history.append(message)
        self._inboxes.setdefault(to_agent, []).append(message)
        return message

    def broadcast(self, from_agent: str, message: str, channel: str) -> list[Message]:
        ch = self._channels.get(channel)
        if not ch:
            return []
        results = []
        for subscriber in ch.subscribers:
            if subscriber == from_agent:
                continue
            msg = self.send_message(from_agent, subscriber, message, channel)
            results.append(msg)
        return results

    def get_inbox(self, agent_id: str) -> list[Message]:
        return list(self._inboxes.get(agent_id, []))

    def clear_inbox(self, agent_id: str):
        self._inboxes[agent_id] = []


agent_communicator = AgentCommunicator()
