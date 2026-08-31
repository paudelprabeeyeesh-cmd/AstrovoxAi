"""Security module — JWT tokens, RBAC, password policy, and input sanitization."""

import re
import time
import hashlib
import secrets
import logging
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class Role(Enum):
    """User roles for RBAC."""
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"


class Permission(Enum):
    """Permissions for RBAC."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    MANAGE_USERS = "manage_users"
    MANAGE_SETTINGS = "manage_settings"


ROLE_PERMISSIONS: dict[Role, list[Permission]] = {
    Role.USER: [Permission.READ, Permission.WRITE],
    Role.MODERATOR: [Permission.READ, Permission.WRITE, Permission.DELETE],
    Role.ADMIN: [Permission.READ, Permission.WRITE, Permission.DELETE, Permission.ADMIN, Permission.MANAGE_USERS, Permission.MANAGE_SETTINGS],
}


@dataclass
class TokenPair:
    """JWT access and refresh token pair."""
    access_token: str
    refresh_token: str
    access_expires_at: float
    refresh_expires_at: float
    token_type: str = "bearer"


@dataclass
class Session:
    """User session."""
    session_id: str
    user_id: str
    ip_address: str
    user_agent: str
    created_at: float
    expires_at: float
    is_active: bool = True
    metadata: dict = field(default_factory=dict)


class PasswordPolicy:
    """Strong password validation."""

    MIN_LENGTH = 8
    MAX_LENGTH = 128
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGIT = True
    REQUIRE_SPECIAL = True
    SPECIAL_CHARS = r"!@#$%^&*()_+-=[]{}|;:,.<>?"

    @classmethod
    def validate(cls, password: str) -> tuple[bool, list[str]]:
        """Validate password against policy. Returns (is_valid, list_of_issues)."""
        issues = []

        if len(password) < cls.MIN_LENGTH:
            issues.append(f"Password must be at least {cls.MIN_LENGTH} characters")

        if len(password) > cls.MAX_LENGTH:
            issues.append(f"Password must be at most {cls.MAX_LENGTH} characters")

        if cls.REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
            issues.append("Password must contain at least one uppercase letter")

        if cls.REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
            issues.append("Password must contain at least one lowercase letter")

        if cls.REQUIRE_DIGIT and not re.search(r'\d', password):
            issues.append("Password must contain at least one digit")

        if cls.REQUIRE_SPECIAL and not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password):
            issues.append("Password must contain at least one special character")

        common_passwords = ['password', '123456', 'qwerty', 'admin', 'letmein']
        if password.lower() in common_passwords:
            issues.append("Password is too common")

        return len(issues) == 0, issues

    @classmethod
    def hash_password(cls, password: str) -> str:
        """Hash a password with salt."""
        salt = secrets.token_hex(16)
        hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}:{hash_obj.hex()}"

    @classmethod
    def verify_password(cls, password: str, hashed: str) -> bool:
        """Verify a password against its hash."""
        try:
            salt, stored_hash = hashed.split(":")
            hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return hash_obj.hex() == stored_hash
        except (ValueError, AttributeError):
            return False


class InputSanitizer:
    """Sanitize user input to prevent injection attacks."""

    @staticmethod
    def sanitize_string(value: str) -> str:
        """Sanitize a string value."""
        if not value:
            return ""
        sanitized = value.strip()
        sanitized = re.sub(r'<script[^>]*>.*?</script>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)
        sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'on\w+\s*=', '', sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'<iframe[^>]*>', '', sanitized, flags=re.IGNORECASE)
        return sanitized

    @staticmethod
    def sanitize_sql(value: str) -> str:
        """Sanitize input for SQL queries."""
        if not value:
            return ""
        dangerous = ["--", ";", "/*", "*/", "xp_", "sp_", "0x"]
        sanitized = value
        for pattern in dangerous:
            sanitized = sanitized.replace(pattern, "")
        return sanitized

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    @staticmethod
    def validate_uuid(value: str) -> bool:
        """Validate UUID format."""
        pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return bool(re.match(pattern, value, re.IGNORECASE))


class SessionManager:
    """Manage user sessions."""

    def __init__(self):
        self._sessions: dict[str, Session] = {}
        self._user_sessions: dict[str, list[str]] = {}

    def create_session(
        self,
        user_id: str,
        ip_address: str,
        user_agent: str,
        ttl: int = 86400,
    ) -> Session:
        """Create a new session."""
        session_id = secrets.token_urlsafe(32)
        now = time.time()

        session = Session(
            session_id=session_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=now,
            expires_at=now + ttl,
        )

        self._sessions[session_id] = session

        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = []
        self._user_sessions[user_id].append(session_id)

        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        if not session.is_active or time.time() > session.expires_at:
            session.is_active = False
            return None

        return session

    def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a session."""
        session = self._sessions.get(session_id)
        if session:
            session.is_active = False
            return True
        return False

    def invalidate_all_user_sessions(self, user_id: str) -> int:
        """Invalidate all sessions for a user."""
        session_ids = self._user_sessions.get(user_id, [])
        count = 0
        for sid in session_ids:
            if self.invalidate_session(sid):
                count += 1
        return count

    def get_active_sessions(self, user_id: str) -> list[Session]:
        """Get all active sessions for a user."""
        session_ids = self._user_sessions.get(user_id, [])
        sessions = []
        for sid in session_ids:
            session = self.get_session(sid)
            if session:
                sessions.append(session)
        return sessions

    def cleanup_expired(self) -> int:
        """Remove expired sessions."""
        now = time.time()
        expired = [
            sid for sid, s in self._sessions.items()
            if not s.is_active or s.expires_at < now
        ]
        for sid in expired:
            session = self._sessions.pop(sid, None)
            if session:
                self._user_sessions.get(session.user_id, []).remove(sid)
        return len(expired)


class AccountLockout:
    """Handle account lockout after repeated failures."""

    def __init__(self, max_attempts: int = 5, lockout_duration: int = 900):
        self._attempts: dict[str, list[float]] = {}
        self._max_attempts = max_attempts
        self._lockout_duration = lockout_duration

    def record_attempt(self, identifier: str) -> bool:
        """Record a failed attempt. Returns True if account is now locked."""
        now = time.time()
        if identifier not in self._attempts:
            self._attempts[identifier] = []

        self._attempts[identifier].append(now)
        cutoff = now - self._lockout_duration
        self._attempts[identifier] = [t for t in self._attempts[identifier] if t >= cutoff]

        return len(self._attempts[identifier]) >= self._max_attempts

    def is_locked(self, identifier: str) -> bool:
        """Check if an account is locked."""
        if identifier not in self._attempts:
            return False

        now = time.time()
        cutoff = now - self._lockout_duration
        recent = [t for t in self._attempts[identifier] if t >= cutoff]
        self._attempts[identifier] = recent

        return len(recent) >= self._max_attempts

    def reset(self, identifier: str):
        """Reset lockout for an identifier."""
        self._attempts.pop(identifier, None)


def check_role_permission(role: Role, permission: Permission) -> bool:
    """Check if a role has a specific permission."""
    return permission in ROLE_PERMISSIONS.get(role, [])


def generate_api_key() -> str:
    """Generate a secure API key."""
    return f"avx_{secrets.token_urlsafe(32)}"


session_manager = SessionManager()
account_lockout = AccountLockout()
input_sanitizer = InputSanitizer()
