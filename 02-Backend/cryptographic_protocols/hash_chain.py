import hashlib
import hmac
from typing import List, Optional


class HashChain:
    def __init__(self, seed: Optional[bytes] = None, length: int = 1000) -> None:
        self._chain: List[bytes] = []
        current = seed or hashlib.sha256(b"seed").digest()
        for _ in range(length):
            self._chain.append(current)
            current = hashlib.sha256(current).digest()
        self._index = length - 1

    def current_value(self) -> bytes:
        return self._chain[self._index]

    def next_value(self) -> bytes:
        self._index = max(0, self._index - 1)
        return self._chain[self._index]

    def verify_chain(self, start: int, end: int, values: List[bytes]) -> bool:
        if start < 0 or end >= len(self._chain) or len(values) != end - start + 1:
            return False
        current = self._chain[start]
        for value in values:
            if not hmac.compare_digest(value, current):
                return False
            current = hashlib.sha256(current).digest()
        return True

    @property
    def root(self) -> bytes:
        return self._chain[0]


class OneWayAccumulator:
    @staticmethod
    def accumulate(values: List[bytes]) -> bytes:
        result = hashlib.sha256(b"one_way").digest()
        for value in values:
            result = hashlib.sha256(result + value).digest()
        return result

    @staticmethod
    def witness(value: bytes, values: List[bytes]) -> bytes:
        result = hashlib.sha256(b"one_way").digest()
        for v in values:
            if v == value:
                continue
            result = hashlib.sha256(result + v).digest()
        return result

    @staticmethod
    def verify(accumulator: bytes, value: bytes, witness: bytes) -> bool:
        computed = hashlib.sha256(witness + value).digest()
        return hmac.compare_digest(computed, accumulator)


class IteratedHashFunction:
    @staticmethod
    def hash(message: bytes, iterations: int = 10000) -> bytes:
        current = message
        for _ in range(iterations):
            current = hashlib.sha256(current).digest()
        return current

    @staticmethod
    def hash_chain(message: bytes, length: int) -> List[bytes]:
        chain = []
        current = message
        for _ in range(length):
            chain.append(current)
            current = hashlib.sha256(current).digest()
        return chain
