"""Identity & Authentication — JWT tokens, sessions, MFA, OAuth."""

import time
import hmac
import hashlib
import secrets
import logging
import re
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class TokenPair:
    """JWT access and refresh token pair."""
    access_token: str
    refresh_token: str
    access_expires_at: float
    refresh_expires_at: float
    token_type: str = "bearer"


@dataclass
class SessionInfo:
    """User session information."""
    session_id: str
    user_id: str
    ip_address: str
    user_agent: str
    created_at: float
    expires_at: float
    is_active: bool = True
    device_fingerprint: str = ""
    last_activity: float = 0.0
    metadata: dict = field(default_factory=dict)


@dataclass
class LoginAttempt:
    """Record of a login attempt."""
    user_id: str
    ip_address: str
    user_agent: str
    timestamp: float
    success: bool
    failure_reason: str = ""


class JWTManager:
    """Manage JWT access and refresh tokens."""

    def __init__(self, secret_key: str = "", algorithm: str = "HS256"):
        self._secret = secret_key or secrets.token_hex(32)
        self._algorithm = algorithm
        self._access_ttl = 900
        self._refresh_ttl = 604800
        self._refresh_tokens: dict[str, dict] = {}

    def create_token_pair(self, user_id: str, claims: dict = None) -> TokenPair:
        """Create access and refresh token pair."""
        now = time.time()

        access_payload = {
            "sub": user_id,
            "iat": now,
            "exp": now + self._access_ttl,
            "type": "access",
        }
        if claims:
            access_payload.update(claims)

        refresh_payload = {
            "sub": user_id,
            "iat": now,
            "exp": now + self._refresh_ttl,
            "type": "refresh",
            "jti": secrets.token_hex(16),
        }

        access_token = self._encode(access_payload)
        refresh_token = self._encode(refresh_payload)

        self._refresh_tokens[refresh_payload["jti"]] = {
            "user_id": user_id,
            "expires_at": now + self._refresh_ttl,
            "used": False,
        }

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            access_expires_at=now + self._access_ttl,
            refresh_expires_at=now + self._refresh_ttl,
        )

    def refresh_access_token(self, refresh_token: str) -> Optional[TokenPair]:
        """Create new token pair from refresh token."""
        payload = self._decode(refresh_token)
        if not payload:
            return None

        if payload.get("type") != "refresh":
            return None

        jti = payload.get("jti")
        stored = self._refresh_tokens.get(jti)
        if not stored or stored["used"] or time.time() > stored["expires_at"]:
            return None

        stored["used"] = True
        return self.create_token_pair(payload["sub"])

    def verify_token(self, token: str) -> Optional[dict]:
        """Verify and decode a token."""
        payload = self._decode(token)
        if not payload:
            return None

        if time.time() > payload.get("exp", 0):
            return None

        return payload

    def _encode(self, payload: dict) -> str:
        """Encode a payload to JWT."""
        import json
        import base64

        header = {"alg": self._algorithm, "typ": "JWT"}
        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b"=")
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=")

        signature_input = f"{header_b64.decode()}.{payload_b64.decode()}"
        signature = hmac.new(
            self._secret.encode(),
            signature_input.encode(),
            hashlib.sha256,
        ).digest()
        signature_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=")

        return f"{signature_input}.{signature_b64.decode()}"

    def _decode(self, token: str) -> Optional[dict]:
        """Decode and verify a JWT."""
        import json
        import base64

        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None

            payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
            payload_json = base64.urlsafe_b64decode(payload_b64)
            return json.loads(payload_json)
        except Exception:
            return None


class SessionManager:
    """Manage user sessions with device tracking."""

    def __init__(self):
        self._sessions: dict[str, SessionInfo] = {}
        self._user_sessions: dict[str, list[str]] = {}

    def create_session(
        self,
        user_id: str,
        ip_address: str,
        user_agent: str,
        ttl: int = 86400,
    ) -> SessionInfo:
        """Create a new session."""
        session_id = secrets.token_urlsafe(32)
        now = time.time()

        device_fp = hashlib.sha256(
            f"{ip_address}:{user_agent}".encode()
        ).hexdigest()[:16]

        session = SessionInfo(
            session_id=session_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=now,
            expires_at=now + ttl,
            device_fingerprint=device_fp,
            last_activity=now,
        )

        self._sessions[session_id] = session

        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = []
        self._user_sessions[user_id].append(session_id)

        return session

    def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """Get active session."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        if not session.is_active or time.time() > session.expires_at:
            session.is_active = False
            return None

        session.last_activity = time.time()
        return session

    def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a session."""
        session = self._sessions.get(session_id)
        if session:
            session.is_active = False
            return True
        return False

    def invalidate_all_sessions(self, user_id: str) -> int:
        """Invalidate all sessions for a user."""
        session_ids = self._user_sessions.get(user_id, [])
        count = 0
        for sid in session_ids:
            if self.invalidate_session(sid):
                count += 1
        return count

    def get_active_sessions(self, user_id: str) -> list[SessionInfo]:
        """Get all active sessions for a user."""
        session_ids = self._user_sessions.get(user_id, [])
        return [self._sessions[sid] for sid in session_ids if sid in self._sessions and self._sessions[sid].is_active]

    def cleanup_expired(self) -> int:
        """Remove expired sessions."""
        now = time.time()
        expired = [sid for sid, s in self._sessions.items() if not s.is_active or s.expires_at < now]
        for sid in expired:
            session = self._sessions.pop(sid, None)
            if session and session.user_id in self._user_sessions:
                try:
                    self._user_sessions[session.user_id].remove(sid)
                except ValueError:
                    pass
        return len(expired)


class AccountLockout:
    """Handle account lockout after repeated failures."""

    def __init__(self, max_attempts: int = 5, lockout_duration: int = 900):
        self._attempts: dict[str, list[float]] = {}
        self._max_attempts = max_attempts
        self._lockout_duration = lockout_duration

    def record_attempt(self, identifier: str) -> bool:
        """Record failed attempt. Returns True if now locked."""
        now = time.time()
        if identifier not in self._attempts:
            self._attempts[identifier] = []

        self._attempts[identifier].append(now)
        cutoff = now - self._lockout_duration
        self._attempts[identifier] = [t for t in self._attempts[identifier] if t >= cutoff]

        return len(self._attempts[identifier]) >= self._max_attempts

    def is_locked(self, identifier: str) -> bool:
        """Check if account is locked."""
        if identifier not in self._attempts:
            return False

        now = time.time()
        cutoff = now - self._lockout_duration
        recent = [t for t in self._attempts[identifier] if t >= cutoff]
        self._attempts[identifier] = recent

        return len(recent) >= self._max_attempts

    def reset(self, identifier: str):
        """Reset lockout."""
        self._attempts.pop(identifier, None)


class LoginHistory:
    """Track login history."""

    def __init__(self):
        self._history: list[LoginAttempt] = []

    def record(self, user_id: str, ip: str, ua: str, success: bool, reason: str = ""):
        """Record a login attempt."""
        self._history.append(LoginAttempt(
            user_id=user_id,
            ip_address=ip,
            user_agent=ua,
            timestamp=time.time(),
            success=success,
            failure_reason=reason,
        ))

    def get_history(self, user_id: str, limit: int = 50) -> list[LoginAttempt]:
        """Get login history for a user."""
        user_history = [h for h in self._history if h.user_id == user_id]
        user_history.sort(key=lambda h: h.timestamp, reverse=True)
        return user_history[:limit]

    def get_recent_failures(self, user_id: str, seconds: int = 3600) -> list[LoginAttempt]:
        """Get recent failed attempts."""
        cutoff = time.time() - seconds
        return [
            h for h in self._history
            if h.user_id == user_id and not h.success and h.timestamp >= cutoff
        ]


class TOTPManager:
    """Time-based One-Time Password for MFA."""

    def __init__(self):
        self._secrets: dict[str, str] = {}

    def generate_secret(self, user_id: str) -> str:
        """Generate TOTP secret for a user."""
        secret = secrets.token_hex(20)
        self._secrets[user_id] = secret
        return secret

    def get_secret(self, user_id: str) -> Optional[str]:
        return self._secrets.get(user_id)

    def verify_code(self, user_id: str, code: str, window: int = 1) -> bool:
        """Verify a TOTP code."""
        secret = self._secrets.get(user_id)
        if not secret:
            return False

        for offset in range(-window, window + 1):
            expected = self._generate_totp(secret, offset)
            if hmac.compare_digest(expected, code):
                return True
        return False

    def _generate_totp(self, secret: str, offset: int = 0) -> str:
        """Generate TOTP code."""
        import struct
        import base64

        counter = int(time.time()) // 30 + offset
        key = bytes.fromhex(secret)
        msg = struct.pack(">Q", counter)
        h = hmac.new(key, msg, hashlib.sha1).digest()
        o = h[19] & 0x0F
        code = struct.unpack(">I", h[o:o + 4])[0] & 0x7FFFFFFF
        return str(code % 1000000).zfill(6)


jwt_manager = JWTManager()
session_manager = SessionManager()
account_lockout = AccountLockout()
login_history = LoginHistory()
totp_manager = TOTPManager()
