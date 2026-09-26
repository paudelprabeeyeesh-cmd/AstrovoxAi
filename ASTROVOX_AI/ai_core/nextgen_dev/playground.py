"""AI playground."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing: Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AIPlaygroundSession:
    session_id: str
    user_id: str
    state: Dict[str, Any] = field(default_factory=dict)


class AIPlayground:
    def __init__(self) -> None:
        self._sessions: Dict[str, AIPlaygroundSession] = {}

    def create_session(self, user_id: str) -> AIPlaygroundSession:
        session_id = uuid.uuid4().hex
        session = AIPlaygroundSession(session_id=session_id, user_id=user_id)
        self._sessions[session_id] = session
        return session

    def update_state(self, session_id: str, state: Dict[str, Any]) -> None:
        session = self._sessions.get(session_id)
        if session:
            session.state.update(state)


ai_playground = AIPlayground()
