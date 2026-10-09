"""
Incognito Mode - Task 119

Provides no-persistence, no-memory operation mode.
Ensures nothing leaks to disk or long-term storage.
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Turn:
    turn_id: str
    role: str
    content: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class IncognitoSession:
    """
    Incognito mode session with no persistence.
    
    Guarantees:
    - No data written to disk
    - No memory extraction or storage
    - No logs of conversation content
    - All data is in-memory only and lost on session end
    """
    
    __slots__ = ('_turns', '_lock', '_session_id', '_started_at', '_ended', '_turn_count')

    def __init__(self, session_id: str):
        self._session_id = session_id
        self._turns: List[Turn] = []
        self._lock = threading.RLock()
        self._started_at = datetime.utcnow()
        self._ended = False
        self._turn_count = 0

    def add_turn(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> Turn:
        """Add a turn to the session (in-memory only)."""
        if self._ended:
            raise RuntimeError("Incognito session has ended")
        with self._lock:
            self._turn_count += 1
            turn = Turn(
                turn_id=f"incognito_{self._session_id}_{self._turn_count}",
                role=role,
                content=content,
                metadata=metadata or {},
            )
            self._turns.append(turn)
            return turn

    def get_turns(self, limit: Optional[int] = None, offset: int = 0) -> List[Turn]:
        """Get turns from the session."""
        with self._lock:
            turns = list(self._turns)
            end = offset + limit if limit else None
            return turns[offset:end]

    def get_session_info(self) -> Dict[str, Any]:
        """Get session metadata (no content)."""
        with self._lock:
            return {
                "session_id": self._session_id,
                "started_at": self._started_at.isoformat(),
                "ended": self._ended,
                "turn_count": self._turn_count,
                "mode": "incognito",
            }

    def end_session(self) -> Dict[str, Any]:
        """End the incognito session and wipe all data."""
        with self._lock:
            self._ended = True
            turn_count = self._turn_count
            self._turns.clear()
            self._turn_count = 0
            return {
                "session_id": self._session_id,
                "mode": "incognito",
                "status": "ended",
                "turns_processed": turn_count,
                "data_retained": False,
            }

    def is_ended(self) -> bool:
        """Check if session has ended."""
        with self._lock:
            return self._ended


class IncognitoMode:
    """
    Incognito mode manager.
    
    Ensures:
    - No conversation persistence
    - No memory extraction
    - No logging of user content
    - Clean state on session end
    """

    def __init__(self):
        self._sessions: Dict[str, IncognitoSession] = {}
        self._lock = threading.RLock()
        self._global_incognito = False

    def start_session(self, session_id: str) -> IncognitoSession:
        """Start a new incognito session."""
        with self._lock:
            if session_id in self._sessions:
                raise ValueError(f"Session {session_id} already exists")
            session = IncognitoSession(session_id)
            self._sessions[session_id] = session
            return session

    def get_session(self, session_id: str) -> Optional[IncognitoSession]:
        """Get an active incognito session."""
        with self._lock:
            return self._sessions.get(session_id)

    def end_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """End an incognito session."""
        with self._lock:
            session = self._sessions.pop(session_id, None)
            if session:
                return session.end_session()
        return None

    def enable_global_incognito(self):
        """Enable global incognito mode for all new sessions."""
        with self._lock:
            self._global_incognito = True

    def disable_global_incognito(self):
        """Disable global incognito mode."""
        with self._lock:
            self._global_incognito = False

    def is_global_incognito(self) -> bool:
        """Check if global incognito mode is enabled."""
        with self._lock:
            return self._global_incognito

    def ensure_no_leak(self, data: Any) -> bool:
        """
        Validate that data contains no persistent identifiers or secrets.
        
        Returns True if data appears safe for incognito mode.
        """
        if data is None:
            return True
        sensitive_patterns = [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            r'\b\d{4}[-]\d{4}[-]\d{4}[-]\d{4}\b',
            r'\b(api[_-]?key|password|secret|token|credential)\b',
        ]
        text = str(data)
        for pattern in sensitive_patterns:
            if re.search(pattern, text, re.I):
                return False
        return True
