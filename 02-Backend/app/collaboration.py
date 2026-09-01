"""AI Collaboration — shared sessions, team chat, live collaboration."""

import time
import logging
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SharedSession:
    """A shared AI session."""
    id: str
    name: str
    participants: list = field(default_factory=list)
    messages: list = field(default_factory=list)
    created_at: float = 0.0
    is_active: bool = True

    def __post_init__(self):
        if self.created_at == 0:
            self.created_at = time.time()


class CollaborationManager:
    """Manage AI collaboration sessions."""

    def __init__(self):
        self._sessions: dict[str, SharedSession] = {}

    def create_session(self, name: str, creator_id: str) -> SharedSession:
        """Create a shared session."""
        import secrets
        session = SharedSession(
            id=secrets.token_hex(8),
            name=name,
            participants=[creator_id],
        )
        self._sessions[session.id] = session
        return session

    def join_session(self, session_id: str, user_id: str):
        session = self._sessions.get(session_id)
        if session and user_id not in session.participants:
            session.participants.append(user_id)

    def add_message(self, session_id: str, user_id: str, content: str):
        session = self._sessions.get(session_id)
        if session:
            session.messages.append({
                "user_id": user_id,
                "content": content,
                "timestamp": time.time(),
            })

    def get_session(self, session_id: str) -> Optional[SharedSession]:
        return self._sessions.get(session_id)


collaboration_manager = CollaborationManager()
