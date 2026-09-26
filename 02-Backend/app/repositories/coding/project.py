"""Project repository for coding agent sessions."""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class ProjectRepository:
    def __init__(self, repo_path: str) -> None:
        self.repo_path = os.path.abspath(repo_path)
        self.sessions: dict[str, dict[str, Any]] = {}

    def create_session(self, user_id: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        session_id = str(uuid.uuid4())
        session = {
            "id": session_id,
            "user_id": user_id,
            "repo_path": self.repo_path,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "active",
            "metadata": metadata or {},
        }
        self.sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        return self.sessions.get(session_id)

    def list_sessions(self, user_id: str | None = None) -> list[dict[str, Any]]:
        sessions = list(self.sessions.values())
        if user_id:
            sessions = [s for s in sessions if s.get("user_id") == user_id]
        return sessions

    def update_session(self, session_id: str, **kwargs: Any) -> dict[str, Any] | None:
        session = self.sessions.get(session_id)
        if not session:
            return None
        session.update(kwargs)
        session["updated_at"] = datetime.now(timezone.utc).isoformat()
        return session

    def close_session(self, session_id: str) -> dict[str, Any] | None:
        return self.update_session(session_id, status="closed")
