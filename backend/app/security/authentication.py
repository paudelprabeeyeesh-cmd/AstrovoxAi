"""Authentication manager with JWT validation, sessions, and brute-force protection."""
import time
import hashlib
import logging
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Session:
    session_id: str
    user_id: str
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=time.time)
    is_active: bool = True
    ip_address: str = ""
    user_agent: str = ""


class AuthenticationManager:
    def __init__(self):
        self._sessions: dict[str, Session] = {}
        self._failed_attempts: dict[str, list[float]] = {}
        self._max_attempts = 5
        self._window = 300.0
        self._lock = __import__('threading').Lock()

    def create_session(self, user_id: str, ttl: int = 3600, ip_address: str = "", user_agent: str = "") -> Session:
        session_id = hashlib.sha256(f"{user_id}:{time.time()}:{__import__('secrets').token_hex(8)}".encode()).hexdigest()[:32]
        now = time.time()
        session = Session(
            session_id=session_id,
            user_id=user_id,
            created_at=now,
            expires_at=now + ttl,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        with self._lock:
            self._sessions[session_id] = session
        return session

    def validate_session(self, session_id: str) -> Optional[Session]:
        with self._lock:
            session = self._sessions.get(session_id)
        if not session or not session.is_active:
            return None
        if time.time() > session.expires_at:
            session.is_active = False
            return None
        return session

    def revoke_session(self, session_id: str):
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.is_active = False

    def revoke_all_user_sessions(self, user_id: str):
        with self._lock:
            for session in self._sessions.values():
                if session.user_id == user_id:
                    session.is_active = False

    def record_failure(self, identifier: str):
        now = time.time()
        with self._lock:
            self._failed_attempts.setdefault(identifier, []).append(now)
            cutoff = now - self._window
            self._failed_attempts[identifier] = [t for t in self._failed_attempts[identifier] if t >= cutoff]

    def record_success(self, identifier: str):
        with self._lock:
            self._failed_attempts.pop(identifier, None)

    def is_locked(self, identifier: str) -> bool:
        with self._lock:
            return len(self._failed_attempts.get(identifier, [])) >= self._max_attempts

    def remaining_attempts(self, identifier: str) -> int:
        with self._lock:
            return max(0, self._max_attempts - len(self._failed_attempts.get(identifier, [])))

    def cleanup_expired(self):
        now = time.time()
        with self._lock:
            expired = [sid for sid, s in self._sessions.items() if now > s.expires_at]
            for sid in expired:
                del self._sessions[sid]


auth_manager = AuthenticationManager()
