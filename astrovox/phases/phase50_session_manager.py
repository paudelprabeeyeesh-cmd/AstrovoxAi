"""Session state management for Astrovox."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Session:
    """A conversational session."""
    id: str
    user_id: str
    messages: list[dict] = field(default_factory=list)
    created: float = field(default_factory=lambda: time.time())
    last_active: float = field(default_factory=lambda: time.time())
    context: dict = field(default_factory=dict)

    def append(self, role: str, content: str) -> dict:
        msg = {"role": role, "content": content}
        self.messages.append(msg)
        self.last_active = time.time()
        return msg

    def to_dict(self) -> dict:
        return {"id": self.id, "user_id": self.user_id, "messages": self.messages,
                "created": self.created, "last_active": self.last_active, "context": self.context}


class SessionManager:
    """Session lifecycle management."""

    def __init__(self, ttl_seconds: float = 3600.0):
        self.ttl = ttl_seconds
        self.sessions: dict[str, Session] = {}

    def create(self, user_id: str) -> Session:
        sid = f"sess_{int(time.time())}_{len(self.sessions)}"
        session = Session(id=sid, user_id=user_id)
        self.sessions[sid] = session
        return session

    def get(self, session_id: str) -> Session | None:
        return self.sessions.get(session_id)

    def append(self, session_id: str, role: str, content: str) -> dict | None:
        session = self.sessions.get(session_id)
        if session is None:
            return None
        return session.append(role, content)

    def active(self, user_id: str) -> Session | None:
        for s in self.sessions.values():
            if s.user_id == user_id and not s.last_active < time.time() - self.ttl:
                return s
        return None

    def cleanup_expired(self) -> int:
        expired = [s.id for s in self.sessions.values()
                   if time.time() - s.last_active > self.ttl]
        for sid in expired:
            del self.sessions[sid]
        return len(expired)

    def count(self) -> int:
        return len(self.sessions)

    def close(self, session_id: str) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
