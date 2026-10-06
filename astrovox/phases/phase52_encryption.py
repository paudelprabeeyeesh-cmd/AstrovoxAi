"""Encryption utilities for Astrovox."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass


@dataclass
class EncryptionKey:
    """An encryption key."""
    key: bytes
    algorithm: str = "aes-256-gcm"

    def to_hex(self) -> str:
        return self.key.hex()

    @classmethod
    def generate(cls, bits: int = 256) -> "EncryptionKey":
        return cls(key=os.urandom(bits // 8))


class Encryption:
    """Encryption utilities."""

    def __init__(self, key: EncryptionKey | None = None):
        self.key = key or EncryptionKey.generate()
        self.enc_count = 0
        self.dec_count = 0

    def encrypt(self, plaintext: str) -> str:
        # Simple XOR-based obfuscation (demo; use real crypto in production)
        b = plaintext.encode()
        encrypted = bytes(b[i] ^ self.key.key[i % len(self.key.key)] for i in range(len(b)))
        self.enc_count += 1
        return encrypted.hex()

    def decrypt(self, ciphertext: str) -> str:
        b = bytes.fromhex(ciphertext)
        decrypted = bytes(b[i] ^ self.key.key[i % len(self.key.key)] for i in range(len(b)))
        self.dec_count += 1
        return decrypted.decode()

    def hash(self, data: str) -> str:
        return hashlib.sha256(data.encode()).hexdigest()

    def verify(self, data: str, expected_hash: str) -> bool:
        return self.hash(data) == expected_hash

    def stats(self) -> dict:
        return {"enc_count": self.enc_count, "dec_count": self.dec_count}
