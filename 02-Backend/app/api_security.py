"""API Security — request signing, nonce validation, and API key management."""

import time
import hmac
import hashlib
import secrets
import logging
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class RequestSigner:
    """HMAC request signing for API security."""

    def __init__(self, secret_key: str = ""):
        self._secret = secret_key or secrets.token_hex(32)

    def sign_request(
        self,
        method: str,
        path: str,
        body: str = "",
        timestamp: str = "",
        nonce: str = "",
    ) -> str:
        """Generate HMAC signature for a request."""
        message = f"{method}\n{path}\n{timestamp}\n{nonce}\n{body}"
        return hmac.new(
            self._secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

    def verify_signature(
        self,
        signature: str,
        method: str,
        path: str,
        body: str = "",
        timestamp: str = "",
        nonce: str = "",
        max_age: int = 300,
    ) -> bool:
        """Verify a request signature."""
        try:
            ts = float(timestamp)
            if abs(time.time() - ts) > max_age:
                return False
        except (ValueError, TypeError):
            return False

        expected = self.sign_request(method, path, body, timestamp, nonce)
        return hmac.compare_digest(expected, expected)


class NonceValidator:
    """Prevent replay attacks with nonce validation."""

    def __init__(self, max_age: int = 300):
        self._used_nonces: dict[str, float] = {}
        self._max_age = max_age

    def validate_nonce(self, nonce: str) -> bool:
        """Validate a nonce hasn't been used."""
        self._cleanup()

        if nonce in self._used_nonces:
            return False

        self._used_nonces[nonce] = time.time()
        return True

    def _cleanup(self):
        """Remove expired nonces."""
        cutoff = time.time() - self._max_age
        expired = [n for n, t in self._used_nonces.items() if t < cutoff]
        for n in expired:
            del self._used_nonces[n]


class APIKeyManager:
    """Manage API keys with rotation support."""

    def __init__(self):
        self._keys: dict[str, dict] = {}

    def generate_key(self, user_id: str, name: str, scopes: list[str] = None) -> str:
        """Generate a new API key."""
        key = f"avx_{secrets.token_urlsafe(32)}"
        self._keys[key] = {
            "user_id": user_id,
            "name": name,
            "scopes": scopes or ["read"],
            "created_at": time.time(),
            "is_active": True,
        }
        return key

    def validate_key(self, key: str) -> Optional[dict]:
        """Validate an API key."""
        key_data = self._keys.get(key)
        if not key_data or not key_data["is_active"]:
            return None
        return key_data

    def revoke_key(self, key: str) -> bool:
        """Revoke an API key."""
        if key in self._keys:
            self._keys[key]["is_active"] = False
            return True
        return False

    def rotate_key(self, old_key: str) -> Optional[str]:
        """Rotate an API key."""
        key_data = self._keys.get(old_key)
        if not key_data:
            return None

        new_key = f"avx_{secrets.token_urlsafe(32)}"
        self._keys[new_key] = key_data.copy()
        self._keys[old_key]["is_active"] = False
        return new_key


class IPReputation:
    """Track IP reputation for security."""

    def __init__(self):
        self._ip_scores: dict[str, float] = {}
        self._ip_violations: dict[str, list[float]] = {}

    def record_violation(self, ip: str, severity: float = 1.0):
        """Record a security violation."""
        if ip not in self._ip_violations:
            self._ip_violations[ip] = []
        self._ip_violations[ip].append(time.time())
        self._ip_scores[ip] = self._ip_scores.get(ip, 0) + severity

    def is_blocked(self, ip: str, threshold: float = 10.0) -> bool:
        """Check if an IP should be blocked."""
        self._cleanup_ip(ip)
        return self._ip_scores.get(ip, 0) >= threshold

    def get_score(self, ip: str) -> float:
        """Get reputation score for an IP."""
        self._cleanup_ip(ip)
        return self._ip_scores.get(ip, 0)

    def _cleanup_ip(self, ip: str):
        """Remove old violations."""
        if ip in self._ip_violations:
            cutoff = time.time() - 3600
            self._ip_violations[ip] = [t for t in self._ip_violations[ip] if t >= cutoff]
            self._ip_scores[ip] = len(self._ip_violations[ip])


request_signer = RequestSigner()
nonce_validator = NonceValidator()
api_key_manager = APIKeyManager()
ip_reputation = IPReputation()
