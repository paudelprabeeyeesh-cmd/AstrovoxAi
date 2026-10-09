import hashlib
import hmac
import os
from typing import Optional, Tuple


_PRIME = 2**256 - 189  # A large prime for modular arithmetic


def _mod_inverse(a: int, m: int = _PRIME) -> int:
    return pow(a, -1, m)


def _mod_exp(base: int, exp: int, m: int = _PRIME) -> int:
    return pow(base, exp, m)


class DiffieHellmanKeyExchange:
    def __init__(self, private_key: Optional[int] = None) -> None:
        self.private_key = private_key or int.from_bytes(os.urandom(32), "big") % _PRIME
        self.public_key = _mod_exp(2, self.private_key)

    def generate_shared_secret(self, peer_public: int) -> bytes:
        shared = _mod_exp(peer_public, self.private_key)
        return hashlib.sha256(str(shared).encode()).digest()

    @staticmethod
    def derive_key(shared_secret: bytes, context: str = "") -> bytes:
        return hashlib.pbkdf2_hmac("sha256", shared_secret, context.encode(), 100000, 32)


class StationToStationProtocol:
    @staticmethod
    def compute_signature(private_key: int, public_key: int, peer_public: int, shared: bytes) -> bytes:
        message = hashlib.sha256(
            str(public_key).encode() + str(peer_public).encode() + shared
        ).digest()
        return hmac.new(private_key.to_bytes(32, "big"), message, hashlib.sha256).digest()

    @staticmethod
    def verify_signature(public_key: int, private_key: int, peer_public: int, shared: bytes, signature: bytes) -> bool:
        expected = StationToStationProtocol.compute_signature(private_key, public_key, peer_public, shared)
        return hmac.compare_digest(signature, expected)


class KeyEncapsulationMechanism:
    @staticmethod
    def encapsulate(public_key: int) -> Tuple[bytes, bytes]:
        ciphertext = os.urandom(32)
        key = hashlib.sha256(str(public_key).encode() + ciphertext).digest()[:32]
        return ciphertext, key

    @staticmethod
    def decapsulate(public_key: int, ciphertext: bytes) -> bytes:
        return hashlib.sha256(str(public_key).encode() + ciphertext).digest()[:32]
