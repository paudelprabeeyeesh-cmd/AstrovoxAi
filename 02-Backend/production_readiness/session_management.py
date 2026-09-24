"""Session management and sticky sessions."""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Session:
    session_id: str
    user_id: str
    backend: str
    created: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=dict)
    sticky: bool = False

    def touch(self, backend: str) -> None:
        self.last_accessed = time.time()
        self.backend = backend

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "backend": self.backend,
            "created": self.created,
            "last_accessed": self.last_accessed,
            "sticky": self.sticky,
        }


class SessionStore:
    def __init__(self) -> None:
        self._sessions: Dict[str, Session] = {}
        self._user_index: Dict[str, str] = {}
        self._lock = threading.Lock()

    def create(self, user_id: str, backend: str, sticky: bool = False) -> Session:
        session_id = f"sess-{int(time.time() * 1000)}-{len(self._sessions) + 1}"
        session = Session(session_id=session_id, user_id=user_id, backend=backend, sticky=sticky)
        with self._lock:
            self._sessions[session_id] = session
            self._user_index[user_id] = session_id
        return session

    def get(self, session_id: str) -> Optional[Session]:
        with self._lock:
            return self._sessions.get(session_id)

    def get_by_user(self, user_id: str) -> Optional[Session]:
        with self._lock:
            session_id = self._user_index.get(user_id)
            if session_id is None:
                return None
            return self._sessions.get(session_id)

    def delete(self, session_id: str) -> None:
        with self._lock:
            session = self._sessions.pop(session_id, None)
            if session is not None:
                self._user_index.pop(session.user_id, None)

    def cleanup(self, ttl: float) -> int:
        cutoff = time.time() - ttl
        removed = 0
        with self._lock:
            expired = [sid for sid, session in self._sessions.items() if session.last_accessed < cutoff]
            for sid in expired:
                session = self._sessions.pop(sid, None)
                if session is not None:
                    self._user_index.pop(session.user_id, None)
                removed += 1
        return removed

    def count(self) -> int:
        with self._lock:
            return len(self._sessions)


class SessionManager:
    def __init__(self) -> None:
        self._store = SessionStore()
        self._backends: Dict[str, List[str]] = {}
        self._lock = threading.Lock()

    def register_backend(self, backend: str, weight: int = 1) -> None:
        with self._lock:
            self._backends[backend] = [backend] * weight

    def _select_backend(self, user_id: str) -> str:
        with self._lock:
            backends = list(self._backends.keys())
        if not backends:
            return "default"
        return backends[hash(user_id) % len(backends)]

    def create_session(self, user_id: str, sticky: bool = False) -> Session:
        backend = self._select_backend(user_id)
        return self._store.create(user_id, backend, sticky)

    def get_session(self, session_id: str) -> Optional[Session]:
        return self._store.get(session_id)

    def get_session_by_user(self, user_id: str) -> Optional[Session]:
        session = self._store.get_by_user(user_id)
        if session is not None:
            session.touch(session.backend)
        return session

    def destroy_session(self, session_id: str) -> None:
        self._store.delete(session_id)

    def sticky_sessions(self) -> List[Session]:
        with self._store._lock:
            return [session for session in self._store._sessions.values() if session.sticky]

    def cleanup(self, ttl: float) -> int:
        return self._store.cleanup(ttl)

    def count(self) -> int:
        return self._store.count()
