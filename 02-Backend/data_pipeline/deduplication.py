import hashlib
import math
from typing import Any


class MinHashLSH:
    def __init__(self, num_hashes: int = 100, num_bands: int = 10) -> None:
        self.num_hashes = num_hashes
        self.num_bands = num_bands
        self.rows_per_band = num_hashes // num_bands
        self._hashes: list[tuple[int, int]] = []
        for i in range(num_hashes):
            a = i * 2654435761 + 1013904223
            b = i * 2246822519 + 3266489917
            self._hashes.append((a % 4294967296, b % 4294967296))
        self._buckets: dict[tuple[int, ...], list[tuple[str, Any]]] = {}

    def _shingle(self, text: str, k: int = 5) -> list[str]:
        text = text.lower()
        return [text[i : i + k] for i in range(max(len(text) - k + 1, 0))]

    def _signature(self, shingles: list[str]) -> list[int]:
        sig = []
        for a, b in self._hashes:
            min_h = min(((hash(shingle) * a + b) % 4294967296) for shingle in shingles)
            sig.append(min_h)
        return sig

    def add(self, doc_id: str, text: str) -> None:
        shingles = self._shingle(text)
        sig = self._signature(shingles)
        for b in range(self.num_bands):
            start = b * self.rows_per_band
            band = tuple(sig[start : start + self.rows_per_band])
            self._buckets.setdefault(band, []).append((doc_id, sig))

    def query(self, text: str, threshold: float = 0.8) -> list[str]:
        shingles = self._shingle(text)
        sig = self._signature(shingles)
        candidates: dict[str, list[int]] = {}
        for b in range(self.num_bands):
            start = b * self.rows_per_band
            band = tuple(sig[start : start + self.rows_per_band])
            for doc_id, existing_sig in self._buckets.get(band, []):
                candidates.setdefault(doc_id, existing_sig)
        results = []
        for doc_id, existing_sig in candidates.items():
            sim = self._jaccard(sig, existing_sig)
            if sim >= threshold:
                results.append(doc_id)
        return results

    @staticmethod
    def _jaccard(a: list[int], b: list[int]) -> float:
        if not a or not b:
            return 0.0
        inter = sum(1 for x, y in zip(a, b) if x == y)
        return inter / len(a)
