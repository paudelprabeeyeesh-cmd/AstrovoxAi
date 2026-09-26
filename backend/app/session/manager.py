"""Session management and token service."""
from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Session:
    session_id: str
    user_id: str
    token: str
    expires_at: datetime
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    revoked: bool = False


class SessionManager:
    def __init__(self, default_ttl_seconds: int = 3600) -> None:
        self._sessions: Dict[str, Session] = {}
        self._default_ttl = default_ttl_seconds

    def create_session(self, user_id: str, ttl_seconds: Optional[int] = None, metadata: Optional[Dict[str, Any]] = None) -> Session:
        session_id = secrets.token_urlsafe(32)
        token = secrets.token_urlsafe(64)
        expires_at = datetime.now(timezone.utc).fromtimestamp(datetime.now(timezone.utc).timestamp() + (ttl_seconds or self._default_ttl))
        session = Session(
            session_id=session_id,
            user_id=user_id,
            token=token,
            expires_at=expires_at,
            metadata=metadata or {},
        )
        self._sessions[session_id] = session
        logger.info("Created session %s for user %s", session_id, user_id)
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        session = self._sessions.get(session_id)
        if session and session.expires_at < datetime.now(timezone.utc):
            self.revoke(session_id)
            return None
        if session:
            session.last_accessed_at = datetime.now(timezone.utc)
        return session

    def revoke(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if session:
            session.revoked = True

    def revoke_all_for_user(self, user_id: str) -> int:
        count = 0
        for session in self._sessions.values():
            if session.user_id == user_id and not session.revoked:
                session.revoked = True
                count += 1
        return count

    def cleanup_expired(self) -> int:
        now = datetime.now(timezone.utc)
        expired = [sid for sid, s in self._sessions.items() if s.expires_at < now]
        for sid in expired:
            del self._sessions[sid]
        return len(expired)


session_manager = SessionManager()
