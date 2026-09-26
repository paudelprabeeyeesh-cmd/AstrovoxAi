"""Interactive playground for API experimentation."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class PlaygroundSession:
    session_id: str
    user_id: str
    state: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class Playground:
    def __init__(self) -> None:
        self._sessions: Dict[str, PlaygroundSession] = {}

    def create_session(self, user_id: str) -> PlaygroundSession:
        session_id = uuid.uuid4().hex
        session = PlaygroundSession(session_id=session_id, user_id=user_id)
        self._sessions[session_id] = session
        return session

    def update_state(self, session_id: str, state: Dict[str, Any]) -> None:
        session = self._sessions.get(session_id)
        if session:
            session.state.update(state)

    def get_session(self, session_id: str) -> Optional[PlaygroundSession]:
        return self._sessions.get(session_id)


playground = Playground()
