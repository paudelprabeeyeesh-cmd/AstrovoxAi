import base64
import hashlib
import hmac
import json
import math
import os
import struct
from typing import Any, Dict, List, Optional, Tuple


class ModernKDF:
    @staticmethod
    def pbkdf2(password: str, salt: Optional[bytes] = None, iterations: int = 100000, key_length: int = 32) -> Tuple[bytes, bytes]:
        salt = salt or os.urandom(32)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations, dklen=key_length)
        return dk, salt

    @staticmethod
    def scrypt(password: str, salt: Optional[bytes] = None, n: int = 64, r: int = 8, p: int = 1, dklen: int = 32) -> Tuple[bytes, bytes]:
        salt = salt or os.urandom(32)
        dk = hashlib.scrypt(password.encode(), salt=salt, n=n, r=r, p=p, dklen=dklen)
        return dk, salt


class AuthenticatedEncryption:
    def __init__(self, key: Optional[bytes] = None) -> None:
        self._key = key or ModernKDF.pbkdf2("default")[0]
        if len(self._key) < 32:
            raise ValueError("Key must be at least 32 bytes")

    def encrypt(self, plaintext: str) -> str:
        iv = os.urandom(16)
        salt = hashlib.sha256(iv).digest()[:16]
        keystream = self._keystream(salt, len(plaintext))
        ciphertext = bytes(p ^ k for p, k in zip(plaintext.encode(), keystream))
        mac = hmac.new(self._key, ciphertext + iv, hashlib.sha256).digest()[:16]
        return base64.b64encode(iv + mac + ciphertext).decode()

    def decrypt(self, b64: str) -> str:
        raw = base64.b64decode(b64.encode())
        if len(raw) < 32:
            raise ValueError("Invalid payload")
        iv, mac, ciphertext = raw[:16], raw[16:32], raw[32:]
        expected = hmac.new(self._key, ciphertext + iv, hashlib.sha256).digest()[:16]
        if not hmac.compare_digest(mac, expected):
            raise ValueError("Authentication failed")
        salt = hashlib.sha256(iv).digest()[:16]
        keystream = self._keystream(salt, len(ciphertext))
        return bytes(c ^ k for c, k in zip(ciphertext, keystream)).decode()

    def _keystream(self, salt: bytes, length: int) -> bytes:
        result = b""
        counter = 0
        while len(result) < length:
            result += hashlib.sha256(self._key + salt + struct.pack(">I", counter)).digest()
            counter += 1
        return result[:length]


class CommitmentScheme:
    def __init__(self) -> None:
        pass

    def commit(self, message: str) -> Tuple[str, str]:
        nonce = os.urandom(32).hex()
        commitment = hashlib.sha256((message + nonce).encode()).hexdigest()
        return commitment, nonce

    def open(self, commitment: str, message: str, nonce: str) -> bool:
        expected = hashlib.sha256((message + nonce).encode()).hexdigest()
        return hmac.compare_digest(expected, commitment)


class PostQuantumKEM:
    @staticmethod
    def kem_pair() -> Tuple[bytes, bytes]:
        public = os.urandom(1560)
        private = hashlib.sha256(public).digest()[:32]
        return public, private

    @staticmethod
    def encapsulate(public: bytes) -> Tuple[bytes, bytes]:
        ciphertext = os.urandom(32)
        key = hashlib.sha256(public + ciphertext).digest()[:32]
        return ciphertext, key

    @staticmethod
    def decapsulate(public: bytes, ciphertext: bytes) -> bytes:
        return hashlib.sha256(public + ciphertext).digest()[:32]
