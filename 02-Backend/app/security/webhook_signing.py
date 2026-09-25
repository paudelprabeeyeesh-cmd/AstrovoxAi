"""HMAC request signing for webhooks.

Outgoing webhooks are signed with a shared secret so receivers can
verify authenticity and integrity. Uses constant-time comparison to
prevent timing attacks.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class WebhookSigner:
    """Signs outgoing webhook payloads and verifies incoming signatures."""

    def __init__(self, secret: str) -> None:
        self._secret = secret.encode("utf-8")

    def sign(self, payload: bytes, timestamp: Optional[float] = None) -> str:
        ts = str(int(timestamp or time.time()))
        message = f"{ts}.{payload.decode('utf-8', errors='replace')}".encode("utf-8")
        signature = hmac.new(self._secret, message, hashlib.sha256).hexdigest()
        return f"t={ts},v1={signature}"

    def verify(self, payload: bytes, signature_header: str, tolerance_seconds: float = 300.0) -> bool:
        if not signature_header:
            return False
        parts = {}
        for segment in signature_header.split(","):
            segment = segment.strip()
            if "=" in segment:
                k, v = segment.split("=", 1)
                parts[k.strip()] = v.strip()
        ts_str = parts.get("t")
        sig = parts.get("v1")
        if not ts_str or not sig:
            return False
        try:
            ts = float(ts_str)
        except ValueError:
            return False
        if abs(time.time() - ts) > tolerance_seconds:
            return False
        expected = self.sign(payload, timestamp=ts)
        expected_sig = expected.split(",v1=")[1]
        return hmac.compare_digest(sig, expected_sig)
