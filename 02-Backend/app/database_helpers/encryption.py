"""Data encryption at rest helper using AES-256-GCM."""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
from dataclasses import dataclass
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Raised when encryption or decryption fails."""


class EncryptionEngine:
    """Encrypt/decrypt sensitive values using AES-256-GCM."""

    def __init__(self, secret_key: str | None = None) -> None:
        key = secret_key or os.getenv("DB_ENCRYPTION_KEY", "")
        if not key:
            raise EncryptionError("DB_ENCRYPTION_KEY is required for field-level encryption")
        digest = hashlib.sha256(key.encode("utf-8")).digest()
        self._key = AESGCM(digest)

    def encrypt(self, plaintext: str) -> str:
        if plaintext is None or plaintext == "":
            return ""
        nonce = os.urandom(12)
        ciphertext = self._key.encrypt(nonce, plaintext.encode("utf-8"), None)
        payload = nonce + ciphertext
        return base64.b64encode(payload).decode("utf-8")

    def decrypt(self, ciphertext_b64: str) -> str:
        if not ciphertext_b64:
            return ""
        try:
            payload = base64.b64decode(ciphertext_b64.encode("utf-8"))
        except Exception as exc:
            raise EncryptionError(f"Invalid base64 ciphertext: {exc}") from exc
        nonce, ciphertext = payload[:12], payload[12:]
        try:
            plaintext = self._key.decrypt(nonce, ciphertext, None)
        except Exception as exc:
            raise EncryptionError(f"Decryption failed: {exc}") from exc
        return plaintext.decode("utf-8")

    def encrypt_dict(self, data: dict[str, Any], fields: list[str]) -> dict[str, Any]:
        encrypted = dict(data)
        for field in fields:
            if field in encrypted and encrypted[field] is not None:
                encrypted[field] = self.encrypt(str(encrypted[field]))
        return encrypted

    def decrypt_dict(self, data: dict[str, Any], fields: list[str]) -> dict[str, Any]:
        decrypted = dict(data)
        for field in fields:
            if field in decrypted and decrypted[field]:
                decrypted[field] = self.decrypt(str(decrypted[field]))
        return decrypted
