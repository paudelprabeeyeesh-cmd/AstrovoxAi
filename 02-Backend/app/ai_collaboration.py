"""AI Collaboration platform."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CollaborationRole(str, Enum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


class CollaborationStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


@dataclass
class CollaborationSession:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    participants: List[str] = field(default_factory=list)
    roles: Dict[str, CollaborationRole] = field(default_factory=dict)
    shared_state: Dict[str, Any] = field(default_factory=dict)
    status: CollaborationStatus = CollaborationStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SharedArtifact:
    artifact_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    artifact_type: str = ""
    content: Dict[str, Any] = field(default_factory=dict)
    author_id: str = ""
    version: int = 1
    created_at: float = field(default_factory=time.time)


class AICollaborationPlatform:
    """Real-time AI collaboration platform."""

    def __init__(self):
        self._sessions: Dict[str, CollaborationSession] = {}
        self._artifacts: Dict[str, SharedArtifact] = {}

    def create_session(self, name: str, owner_id: str, participants: Optional[List[str]] = None) -> CollaborationSession:
        session = CollaborationSession(name=name, participants=[owner_id] + (participants or []), roles={owner_id: CollaborationRole.OWNER})
        self._sessions[session.session_id] = session
        logger.info("Created collaboration session: %s", name)
        return session

    def join_session(self, session_id: str, user_id: str, role: CollaborationRole = CollaborationRole.VIEWER) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        if user_id not in session.participants:
            session.participants.append(user_id)
        session.roles[user_id] = role
        return True

    def leave_session(self, session_id: str, user_id: str) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        session.participants = [p for p in session.participants if p != user_id]
        session.roles.pop(user_id, None)
        return True

    def update_shared_state(self, session_id: str, key: str, value: Any, user_id: str) -> bool:
        session = self._sessions.get(session_id)
        if not session or user_id not in session.participants:
            return False
        session.shared_state[key] = value
        session.updated_at = time.time()
        return True

    def create_artifact(self, session_id: str, artifact_type: str, content: Dict[str, Any], author_id: str) -> Optional[SharedArtifact]:
        session = self._sessions.get(session_id)
        if not session or author_id not in session.participants:
            return None
        artifact = SharedArtifact(session_id=session_id, artifact_type=artifact_type, content=content, author_id=author_id)
        self._artifacts[artifact.artifact_id] = artifact
        return artifact

    def get_session_artifacts(self, session_id: str) -> List[SharedArtifact]:
        return [a for a in self._artifacts.values() if a.session_id == session_id]

    def get_session(self, session_id: str) -> Optional[CollaborationSession]:
        return self._sessions.get(session_id)


ai_collaboration_platform = AICollaborationPlatform()
