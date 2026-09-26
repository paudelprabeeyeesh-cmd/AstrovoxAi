import logging
from dataclasses import dataclass
from typing import List, Optional
import hashlib
import random

logger = logging.getLogger(__name__)


@dataclass
class MinHashConfig:
    num_hashes: int = 128
    num_bands: int = 16
    bands_rows: int = 8


class MinHash:
    def __init__(self, config: Optional[MinHashConfig] = None):
        self.config = config or MinHashConfig()
        self.hash_funcs = [self._make_hash_func(i) for i in range(self.config.num_hashes)]

    def _make_hash_func(self, seed: int):
        def hash_func(x: bytes) -> int:
            return int(hashlib.sha256(bytes([seed]) + x).hexdigest(), 16)
        return hash_func

    def signature(self, tokens: List[str]) -> List[int]:
        joined = " ".join(tokens).encode("utf-8")
        return [min(h(joined) for h in self.hash_funcs) for _ in range(self.config.num_hashes)]

    def jaccard(self, sig1: List[int], sig2: List[int]) -> float:
        if len(sig1) != len(sig2):
            return 0.0
        return sum(1 for a, b in zip(sig1, sig2) if a == b) / len(sig1)


class LSH:
    def __init__(self, config: Optional[MinHashConfig] = None):
        self.config = config or MinHashConfig()
        self.buckets = {}

    def _band_hash(self, band: List[int], band_id: int) -> str:
        return f"{band_id}:{hash(tuple(band))}"

    def index(self, doc_id: str, signature: List[int]):
        rows = self.config.bands_rows
        for band_id in range(self.config.num_bands):
            start = band_id * rows
            band = signature[start:start + rows]
            key = self._band_hash(band, band_id)
            self.buckets.setdefault(key, []).append(doc_id)

    def query(self, signature: List[int]) -> List[str]:
        rows = self.config.bands_rows
        candidates = set()
        for band_id in range(self.config.num_bands):
            start = band_id * rows
            band = signature[start:start + rows]
            key = self._band_hash(band, band_id)
            if key in self.buckets:
                candidates.update(self.buckets[key])
        return list(candidates)
