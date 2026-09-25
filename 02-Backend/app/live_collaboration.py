"""Live collaboration features."""

from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class CollaborationAction(Enum):
    JOIN = "join"
    LEAVE = "leave"
    EDIT = "edit"
    CURSOR_MOVE = "cursor_move"
    SELECTION_CHANGE = "selection_change"


@dataclass
class CollaborationSession:
    session_id: str
    resource_id: str
    participants: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CollaborationEvent:
    session_id: str
    user_id: str
    action: CollaborationAction
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class LiveCollaboration:
    _sessions: Dict[str, CollaborationSession] = {}

    @classmethod
    def create_session(cls, resource_id: str, user_id: str) -> CollaborationSession:
        session_id = f"collab_{resource_id}_{datetime.now(timezone.utc).timestamp()}"
        session = CollaborationSession(session_id=session_id, resource_id=resource_id)
        session.participants.add(user_id)
        cls._sessions[session_id] = session
        return session

    @classmethod
    def join_session(cls, session_id: str, user_id: str) -> bool:
        session = cls._sessions.get(session_id)
        if session:
            session.participants.add(user_id)
            return True
        return False

    @classmethod
    def leave_session(cls, session_id: str, user_id: str) -> None:
        session = cls._sessions.get(session_id)
        if session:
            session.participants.discard(user_id)

    @classmethod
    def broadcast_event(cls, session_id: str, event: CollaborationEvent) -> List[str]:
        session = cls._sessions.get(session_id)
        if session:
            return list(session.participants)
        return []
