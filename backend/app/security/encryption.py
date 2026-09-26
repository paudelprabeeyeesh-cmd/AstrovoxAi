"""Encryption and hashing services."""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
from dataclasses import dataclass
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)


@dataclass
class EncryptionResult:
    ciphertext: bytes
    nonce: bytes
    tag: Optional[bytes] = None


class EncryptionService:
    def __init__(self, key: Optional[bytes] = None) -> None:
        self._key = key or AESGCM.generate_key(bit_length=256)

    def encrypt(self, plaintext: bytes, associated_data: Optional[bytes] = None) -> EncryptionResult:
        aesgcm = AESGCM(self._key)
        nonce = os.urandom(12)
        ct = aesgcm.encrypt(nonce, plaintext, associated_data)
        return EncryptionResult(ciphertext=ct[:-16], nonce=nonce, tag=ct[-16:])

    def decrypt(self, result: EncryptionResult, associated_data: Optional[bytes] = None) -> bytes:
        aesgcm = AESGCM(self._key)
        return aesgcm.decrypt(result.nonce, result.ciphertext + result.tag, associated_data)

    def rotate_key(self) -> bytes:
        self._key = AESGCM.generate_key(bit_length=256)
        return self._key


class HashingService:
    @staticmethod
    def sha256(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def hmac_sha256(key: bytes, data: bytes) -> str:
        return hmac.new(key, data, hashlib.sha256).hexdigest()

    @staticmethod
    def hash_password(password: str, salt: Optional[bytes] = None) -> str:
        salt = salt or os.urandom(16)
        hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
        return salt.hex() + ":" + hashed.hex()

    @staticmethod
    def verify_password(password: str, stored: str) -> bool:
        try:
            salt_hex, hash_hex = stored.split(":")
            salt = bytes.fromhex(salt_hex)
            expected = bytes.fromhex(hash_hex)
            actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
            return hmac.compare_digest(expected, actual)
        except ValueError:
            return False


encryption_service = EncryptionService()
hashing_service = HashingService()
