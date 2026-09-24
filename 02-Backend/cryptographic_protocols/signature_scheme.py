import hashlib
import hmac
import os
from typing import Tuple


class HMACSignatureScheme:
    def __init__(self, key: Optional[bytes] = None) -> None:
        self._key = key or os.urandom(32)

    def sign(self, message: bytes) -> bytes:
        return hmac.new(self._key, message, hashlib.sha256).digest()

    def verify(self, message: bytes, signature: bytes) -> bool:
        expected = hmac.new(self._key, message, hashlib.sha256).digest()
        return hmac.compare_digest(signature, expected)


class HashBasedSignature:
    @staticmethod
    def generate_keypair() -> Tuple[bytes, bytes]:
        key = os.urandom(32)
        return key, key

    @staticmethod
    def sign(key: bytes, message: bytes) -> bytes:
        return hashlib.sha256(key + message).digest()

    @staticmethod
    def verify(key: bytes, message: bytes, signature: bytes) -> bool:
        expected = hashlib.sha256(key + message).digest()
        return hmac.compare_digest(signature, expected)


class MerkleSignatureScheme:
    def __init__(self, height: int = 4) -> None:
        self._height = height
        self._private_keys = [os.urandom(32) for _ in range(2**height)]
        self._public_key = hashlib.sha256(b"".join(self._private_keys)).digest()
        self._auth_paths = self._build_auth_paths()

    def _build_auth_paths(self) -> list:
        paths = []
        for i in range(len(self._private_keys)):
            path = []
            idx = i
            for _ in range(self._height):
                sibling = hashlib.sha256(self._private_keys[idx ^ 1]).digest() if idx ^ 1 < len(self._private_keys) else b""
                path.append(sibling)
                idx >>= 1
            paths.append(path)
        return paths

    def sign(self, index: int, message: bytes) -> Tuple[bytes, list]:
        if index >= len(self._private_keys):
            raise ValueError("Key index out of range")
        return self._private_keys[index], self._auth_paths[index]

    @staticmethod
    def verify(public_key: bytes, index: int, message: bytes, private_key: bytes, auth_path: list) -> bool:
        current = hashlib.sha256(private_key).digest()
        for sibling in auth_path:
            if index % 2 == 0:
                current = hashlib.sha256(current + sibling).digest()
            else:
                current = hashlib.sha256(sibling + current).digest()
            index >>= 1
        return hmac.compare_digest(current, public_key)

    @property
    def public_key(self) -> bytes:
        return self._public_key
