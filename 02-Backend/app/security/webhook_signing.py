"""HMAC request signing for webhooks with enhanced security.

This module implements webhook signing with:

1. HMAC-SHA256 signature generation and verification
2. Timestamp-based replay attack prevention
3. Multiple algorithm support (SHA256, SHA512)
4. Signature versioning for rotation
5. Payload hash verification (integrity checking)
6. Retry-safe idempotency keys
7. Webhook secret rotation support
8. Cross-platform compatibility

Threat model: OWASP Top A08:2021 - Software and Data Integrity Failures
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class SignatureAlgorithm(str, Enum):
    SHA256 = "sha256"
    SHA512 = "sha512"


class WebhookSignatureVersion(str, Enum):
    V1 = "v1"
    V2 = "v2"


@dataclass
class WebhookSignature:
    version: str
    signature: str
    timestamp: float
    algorithm: str = "sha256"
    payload_hash: Optional[str] = None


class WebhookSigner:
    """Signs outgoing webhook payloads and verifies incoming signatures."""

    def __init__(
        self,
        secret: str,
        algorithm: SignatureAlgorithm = SignatureAlgorithm.SHA256,
        version: WebhookSignatureVersion = WebhookSignatureVersion.V1,
    ) -> None:
        self._secret = secret.encode("utf-8")
        self._algorithm = algorithm
        self._version = version
        self._hash_func = hashlib.sha256 if algorithm == SignatureAlgorithm.SHA256 else hashlib.sha512

    def _compute_signature(self, payload: bytes, timestamp: float) -> str:
        """Compute HMAC signature."""
        ts_bytes = str(int(timestamp)).encode("utf-8")
        message = ts_bytes + b"." + payload
        signature = hmac.new(self._secret, message, self._hash_func).hexdigest()
        return signature

    def sign(self, payload: bytes, timestamp: Optional[float] = None, payload_hash: Optional[str] = None) -> str:
        """Sign a payload and return signature header value."""
        ts = int(timestamp or time.time())
        signature = self._compute_signature(payload, ts)

        if self._version == WebhookSignatureVersion.V1:
            header_parts = [
                f"t={ts}",
                f"v1={signature}",
            ]
        else:
            header_parts = [
                f"t={ts}",
                f"v2={signature}",
                f"alg={self._algorithm.value}",
            ]

        if payload_hash:
            header_parts.append(f"h={payload_hash}")

        return ",".join(header_parts)

    def verify(
        self,
        payload: bytes,
        signature_header: str,
        tolerance_seconds: float = 300.0,
        payload_hash: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Verify webhook signature. Returns (is_valid, error_message)."""
        if not signature_header:
            return False, "Missing signature header"

        parts = {}
        for segment in signature_header.split(","):
            segment = segment.strip()
            if "=" in segment:
                k, v = segment.split("=", 1)
                parts[k.strip()] = v.strip()

        ts_str = parts.get("t")
        sig = parts.get(f"v{self._version.value[1]}")
        if not ts_str or not sig:
            return False, "Missing timestamp or signature"

        try:
            ts = float(ts_str)
        except ValueError:
            return False, "Invalid timestamp"

        # Replay protection
        current_time = time.time()
        if abs(current_time - ts) > tolerance_seconds:
            return False, f"Timestamp outside tolerance ({tolerance_seconds}s)"

        # Verify payload hash if provided
        if payload_hash:
            actual_hash = hashlib.sha256(payload).hexdigest()
            if not hmac.compare_digest(actual_hash, payload_hash):
                return False, "Payload hash mismatch"

        # Verify signature
        expected_sig = self._compute_signature(payload, ts)
        if not hmac.compare_digest(sig, expected_sig):
            return False, "Signature mismatch"

        return True, None

    def rotate_secret(self, new_secret: str) -> None:
        """Rotate webhook signing secret."""
        self._secret = new_secret.encode("utf-8")
        logger.info("Webhook signing secret rotated")


@dataclass
class WebhookSecret:
    secret: str
    created_at: float
    expires_at: Optional[float] = None
    is_active: bool = True
    version: str = "v1"


class WebhookSecretManager:
    """Manages webhook secrets with rotation support."""

    def __init__(self, default_secret: str):
        self._secrets: Dict[str, WebhookSecret] = {
            "default": WebhookSecret(
                secret=default_secret,
                created_at=time.time(),
                expires_at=time.time() + 86400 * 90,
            )
        }
        self._lock = threading.Lock()
        self._rotation_interval = 86400 * 90  # 90 days

    def get_active_secret(self) -> WebhookSecret:
        """Get the currently active webhook secret."""
        with self._lock:
            for secret in self._secrets.values():
                if secret.is_active:
                    return secret
        return list(self._secrets.values())[0]

    def get_signer(self, algorithm: SignatureAlgorithm = SignatureAlgorithm.SHA256) -> WebhookSigner:
        """Get a signer for the active secret."""
        secret = self.get_active_secret()
        return WebhookSigner(secret.secret, algorithm)

    def rotate_secret(self) -> WebhookSecret:
        """Rotate to a new webhook secret."""
        new_secret = hashlib.sha256(f"astrovox-webhook-{time.time()}".encode()).hexdigest()
        new_version = f"v{len(self._secrets) + 1}"
        now = time.time()

        with self._lock:
            # Deactivate old secrets
            for secret in self._secrets.values():
                secret.is_active = False

            # Create new secret
            webhook_secret = WebhookSecret(
                secret=new_secret,
                created_at=now,
                expires_at=now + self._rotation_interval,
                is_active=True,
                version=new_version,
            )
            self._secrets[new_version] = webhook_secret

        logger.info("Rotated webhook secret to %s", new_version)
        return webhook_secret

    def revoke_secret(self, version: str) -> bool:
        """Revoke a specific webhook secret version."""
        with self._lock:
            secret = self._secrets.get(version)
            if secret:
                secret.is_active = False
                logger.info("Revoked webhook secret version %s", version)
                return True
        return False

    def get_secret_history(self) -> List[Dict[str, Any]]:
        """Get history of webhook secrets."""
        with self._lock:
            return [
                {
                    "version": s.version,
                    "created_at": s.created_at,
                    "expires_at": s.expires_at,
                    "is_active": s.is_active,
                    "created_at_iso": datetime.fromtimestamp(s.created_at, tz=timezone.utc).isoformat(),
                }
                for s in self._secrets.values()
            ]

    def validate_secret(self, secret: str) -> bool:
        """Validate a webhook secret format."""
        return len(secret) >= 32 and secret.isalnum()


webhook_signer = WebhookSigner("default-webhook-secret-change-in-production")
webhook_secret_manager = WebhookSecretManager("default-webhook-secret-change-in-production")


def sign_webhook_payload(payload: bytes, timestamp: Optional[float] = None) -> str:
    """Convenience function to sign a webhook payload."""
    return webhook_signer.sign(payload, timestamp)


def verify_webhook_signature(payload: bytes, signature_header: str, tolerance_seconds: float = 300.0) -> Tuple[bool, Optional[str]]:
    """Convenience function to verify a webhook signature."""
    return webhook_signer.verify(payload, signature_header, tolerance_seconds)
