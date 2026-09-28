from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from models.llm.agents.tools import Tool, ToolResult


@dataclass
class Message:
    sender: str
    receiver: str
    content: Any
    msg_type: str = "message"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "content": self.content,
            "msg_type": self.msg_type,
            "metadata": self.metadata,
        }


@dataclass
class AgentConfig:
    name: str
    role: str
    capabilities: list[str]
    tools: dict[str, Tool]
    metadata: dict[str, Any] = field(default_factory=dict)


class Agent:
    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self.inbox: list[Message] = []

    def send(self, receiver: str, content: Any, msg_type: str = "message", metadata: dict[str, Any] | None = None) -> Message:
        return Message(sender=self.config.name, receiver=receiver, content=content, msg_type=msg_type, metadata=metadata or {})

    def receive(self, message: Message) -> None:
        self.inbox.append(message)

    def process(self, message: Message, team: "AgentTeam") -> Any:
        raise NotImplementedError


class AgentTeam:
    def __init__(self) -> None:
        self._agents: dict[str, Agent] = {}
        self._message_log: list[Message] = []
        self._handlers: dict[str, Callable[[Message, "AgentTeam"], Any]] = {}

    def add_agent(self, agent: Agent) -> None:
        self._agents[agent.config.name] = agent

    def remove_agent(self, name: str) -> None:
        self._agents.pop(name, None)

    def get_agent(self, name: str) -> Agent | None:
        return self._agents.get(name)

    def broadcast(self, sender: str, content: Any, msg_type: str = "broadcast") -> list[Message]:
        messages: list[Message] = []
        for name, agent in self._agents.items():
            if name != sender:
                msg = agent.send(name, content, msg_type=msg_type)
                messages.append(msg)
        self._message_log.extend(messages)
        for msg in messages:
            receiver = self._agents.get(msg.receiver)
            if receiver is not None:
                receiver.receive(msg)
        return messages

    def send(self, sender: str, receiver: str, content: Any, msg_type: str = "message", metadata: dict[str, Any] | None = None) -> Message | None:
        sender_agent = self._agents.get(sender)
        receiver_agent = self._agents.get(receiver)
        if sender_agent is None or receiver_agent is None:
            return None
        msg = sender_agent.send(receiver, content, msg_type=msg_type, metadata=metadata)
        self._message_log.append(msg)
        receiver_agent.receive(msg)
        return msg

    def register_handler(self, msg_type: str, handler: Callable[[Message, "AgentTeam"], Any]) -> None:
        self._handlers[msg_type] = handler

    def run_round(self) -> list[Any]:
        results: list[Any] = []
        for name, agent in self._agents.items():
            for msg in list(agent.inbox):
                agent.inbox.remove(msg)
                handler = self._handlers.get(msg.msg_type)
                if handler is not None:
                    results.append(handler(msg, self))
        return results

    def get_message_log(self) -> list[dict[str, Any]]:
        return [msg.to_dict() for msg in self._message_log]
