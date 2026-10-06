"""Conversation memory: session-based chat history with recall."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ConversationMessage:
    """A single message in a conversation."""
    role: str = "user"
    content: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content,
                "timestamp": self.timestamp}

    @classmethod
    def from_dict(cls, d: dict) -> "ConversationMessage":
        d = d.copy()
        d.setdefault("timestamp", time.time())
        return cls(**d)


@dataclass
class Conversation:
    """A conversation session with its message history."""
    id: str = field(default_factory=lambda: f"conv_{int(time.time())}")
    title: str = "Untitled conversation"
    messages: list[ConversationMessage] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def append(self, role: str, content: str) -> ConversationMessage:
        msg = ConversationMessage(role=role, content=content)
        self.messages.append(msg)
        return msg

    def recent(self, n: int = 5) -> list[ConversationMessage]:
        return self.messages[-n:]

    def to_dict(self) -> dict:
        return {"id": self.id, "title": self.title,
                "messages": [m.to_dict() for m in self.messages],
                "metadata": self.metadata}

    @classmethod
    def from_dict(cls, d: dict) -> "Conversation":
        return cls(**d)


class ConversationMemory:
    """Persistent storage of conversation sessions."""

    def __init__(self, path: str = "data/conversations.json"):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self._path.read_text())
            self._conversations: dict[str, Conversation] = {
                c["id"]: Conversation.from_dict(c) for c in data}
        except Exception:
            self._conversations = {}

    def _save(self) -> None:
        self._path.write_text(json.dumps([c.to_dict() for c in self._conversations.values()]))

    def create(self, title: str = "Untitled conversation") -> Conversation:
        conv = Conversation(title=title)
        self._conversations[conv.id] = conv
        self._save()
        return conv

    def get(self, conv_id: str) -> Conversation | None:
        return self._conversations.get(conv_id)

    def start(self, title: str = "Untitled conversation") -> Conversation:
        for c in self._conversations.values():
            if c.id.startswith("conv_"):
                return c
        return self.create(title)

    def append(self, conv_id: str, role: str, content: str) -> ConversationMessage:
        conv = self.get(conv_id) or self.create()
        msg = conv.append(role, content)
        self._conversations[conv.id] = conv
        self._save()
        return msg

    def history(self, conv_id: str, limit: int = 50) -> list[dict]:
        conv = self.get(conv_id)
        if conv is None:
            return []
        return [m.to_dict() for m in conv.recent(limit)]

    def summary(self, conv_id: str) -> str:
        conv = self.get(conv_id)
        if conv is None:
            return "No conversation"
        return f"{conv.title}: {len(conv.messages)} messages"

    def list_conversations(self) -> list[dict]:
        return [{"id": c.id, "title": c.title, "message_count": len(c.messages)}
                for c in self._conversations.values()]

    def delete(self, conv_id: str) -> bool:
        if conv_id in self._conversations:
            del self._conversations[conv_id]
            self._save()
            return True
        return False
