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
        self._public_key = self._build_root()
        self._auth_paths = self._build_auth_paths()

    def _build_root(self) -> bytes:
        nodes = [hashlib.sha256(k).digest() for k in self._private_keys]
        while len(nodes) > 1:
            next_level = []
            for i in range(0, len(nodes), 2):
                left = nodes[i]
                right = nodes[i + 1] if i + 1 < len(nodes) else nodes[i]
                next_level.append(hashlib.sha256(left + right).digest())
            nodes = next_level
        return nodes[0]

    def _build_auth_paths(self) -> list:
        paths = []
        leaf_count = len(self._private_keys)
        for i in range(leaf_count):
            path = []
            idx = i
            level_nodes = [hashlib.sha256(k).digest() for k in self._private_keys]
            while len(level_nodes) > 1:
                sibling_idx = idx ^ 1
                sibling = level_nodes[sibling_idx] if sibling_idx < len(level_nodes) else level_nodes[idx]
                path.append(sibling)
                idx >>= 1
                next_level = []
                for j in range(0, len(level_nodes), 2):
                    left = level_nodes[j]
                    right = level_nodes[j + 1] if j + 1 < len(level_nodes) else level_nodes[j]
                    next_level.append(hashlib.sha256(left + right).digest())
                level_nodes = next_level
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
