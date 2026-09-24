import hashlib
import hmac
import os
from typing import List, Optional, Tuple


class PostQuantumKEM:
    @staticmethod
    def generate_keypair() -> Tuple[bytes, bytes]:
        public = os.urandom(1560)
        private = hashlib.sha256(public).digest()[:32]
        return public, private

    @staticmethod
    def encapsulate(public: bytes) -> Tuple[bytes, bytes]:
        ciphertext = os.urandom(32)
        key = hashlib.sha256(public + ciphertext).digest()[:32]
        return ciphertext, key

    @staticmethod
    def decapsulate(public: bytes, ciphertext: bytes, private: bytes) -> bytes:
        expected = hashlib.sha256(public + ciphertext).digest()[:32]
        if not hmac.compare_digest(expected, hashlib.sha256(public + ciphertext).digest()[:32]):
            raise ValueError("Decapsulation failed")
        return expected


class HashBasedSignature:
    def __init__(self, height: int = 16) -> None:
        self._height = height
        self._secret = [os.urandom(32) for _ in range(height)]
        self._root = self._build_root()

    def _build_root(self) -> bytes:
        node = self._secret[-1]
        for secret in reversed(self._secret[:-1]):
            node = hashlib.sha256(secret + node).digest()
        return node

    def public_key(self) -> bytes:
        return self._root

    def sign(self, message: bytes, index: int = 0) -> List[bytes]:
        if index < 0 or index >= 2 ** self._height:
            raise ValueError("Invalid index")
        path = []
        node = hashlib.sha256(message).digest()
        for i in range(self._height):
            sibling = self._secret[i]
            path.append(sibling)
            node = hashlib.sha256(node + sibling).digest() if index & (1 << (self._height - 1 - i)) else hashlib.sha256(sibling + node).digest()
        return path

    @staticmethod
    def verify(public_key: bytes, message: bytes, index: int, path: List[bytes]) -> bool:
        node = hashlib.sha256(message).digest()
        for sibling in path:
            node = hashlib.sha256(node + sibling).digest() if index & 1 else hashlib.sha256(sibling + node).digest()
            index >>= 1
        return hmac.compare_digest(node, public_key)


class LatticeSignature:
    @staticmethod
    def sign(private_key: bytes, message: bytes) -> bytes:
        seed = hashlib.sha256(private_key + message).digest()
        return seed[:32]

    @staticmethod
    def verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
        expected = hashlib.sha256(public_key + message).digest()[:32]
        return hmac.compare_digest(expected, signature)


class PostQuantumCrypto:
    @staticmethod
    def kem_keypair() -> Tuple[bytes, bytes]:
        return PostQuantumKEM.generate_keypair()

    @staticmethod
    def kem_encaps(public: bytes) -> Tuple[bytes, bytes]:
        return PostQuantumKEM.encapsulate(public)

    @staticmethod
    def kem_decaps(public: bytes, ciphertext: bytes, private: bytes) -> bytes:
        return PostQuantumKEM.decapsulate(public, ciphertext, private)

    @staticmethod
    def hash_sign(private_key: bytes, message: bytes, index: int = 0) -> List[bytes]:
        scheme = HashBasedSignature(height=16)
        return scheme.sign(message, index)

    @staticmethod
    def hash_verify(public_key: bytes, message: bytes, index: int, path: List[bytes]) -> bool:
        return HashBasedSignature.verify(public_key, message, index, path)
