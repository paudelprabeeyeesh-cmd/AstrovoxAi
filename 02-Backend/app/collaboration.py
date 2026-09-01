"""AI Collaboration — shared sessions, team chat, live collaboration.

Phase 364 — Collaboration Platform:
Shared workspaces, comments, mentions, live collaboration, shared AI sessions,
activity timeline, team notifications, presence indicators, file sharing,
discussion threads.
"""

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


# ============================================================================
# Phase 364 — Collaboration Platform
# ============================================================================

@dataclass
class Comment:
    """A comment on a shared resource."""
    id: str
    author_id: str
    content: str
    resource_type: str
    resource_id: str
    created_at: float
    mentions: list = field(default_factory=list)


class CommentManager:
    """Manage comments on shared resources."""

    def __init__(self):
        self._comments: list[Comment] = []

    def add(self, author_id: str, content: str, resource_type: str, resource_id: str) -> Comment:
        """Add a comment."""
        import secrets
        mentions = [word[1:] for word in content.split() if word.startswith("@")]
        comment = Comment(
            id=secrets.token_hex(8),
            author_id=author_id,
            content=content,
            resource_type=resource_type,
            resource_id=resource_id,
            created_at=time.time(),
            mentions=mentions,
        )
        self._comments.append(comment)
        return comment

    def get_for_resource(self, resource_type: str, resource_id: str) -> list[Comment]:
        """Get comments for a resource."""
        return [
            c for c in self._comments
            if c.resource_type == resource_type and c.resource_id == resource_id
        ]


class PresenceTracker:
    """Track user presence in shared sessions."""

    def __init__(self):
        self._presence: dict = {}

    def set_online(self, user_id: str, session_id: str):
        """Mark user as online."""
        self._presence[f"{user_id}:{session_id}"] = {
            "user_id": user_id,
            "session_id": session_id,
            "status": "online",
            "last_seen": time.time(),
        }

    def set_offline(self, user_id: str, session_id: str):
        """Mark user as offline."""
        key = f"{user_id}:{session_id}"
        if key in self._presence:
            self._presence[key]["status"] = "offline"

    def get_online_users(self, session_id: str) -> list:
        """Get online users in a session."""
        now = time.time()
        return [
            p for p in self._presence.values()
            if p["session_id"] == session_id and now - p["last_seen"] < 60
        ]


class NotificationCenter:
    """Manage team notifications."""

    def __init__(self):
        self._notifications: list = []

    def notify(self, user_id: str, notification_type: str, message: str, source: str = ""):
        """Send a notification."""
        import secrets
        self._notifications.append({
            "id": secrets.token_hex(8),
            "user_id": user_id,
            "type": notification_type,
            "message": message,
            "source": source,
            "read": False,
            "timestamp": time.time(),
        })

    def get_unread(self, user_id: str) -> list:
        """Get unread notifications."""
        return [n for n in self._notifications if n["user_id"] == user_id and not n["read"]]

    def mark_read(self, notification_id: str):
        """Mark a notification as read."""
        for n in self._notifications:
            if n["id"] == notification_id:
                n["read"] = True
                return True
        return False


comment_manager = CommentManager()
presence_tracker = PresenceTracker()
notification_center = NotificationCenter()
