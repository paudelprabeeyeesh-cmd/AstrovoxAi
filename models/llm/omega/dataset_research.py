"""Omega-3: Dataset engineering with deduplication, filtering, and curriculum learning."""

import hashlib
import logging
from dataclasses import dataclass
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class DedupConfig:
    min_hash_threshold: float = 0.8
    sim_hash_bits: int = 64
    bloom_filter_size: int = 1_000_000
    bloom_filter_hashes: int = 7


class MinHashDedup:
    def __init__(self, num_hashes: int = 128, num_shingles: int = 5):
        self.num_hashes = num_hashes
        self.num_shingles = num_shingles
        self._seen_hashes: set[int] = set()

    def shingles(self, text: str) -> list[str]:
        tokens = text.lower().split()
        return [" ".join(tokens[i : i + self.num_shingles]) for i in range(max(len(tokens) - self.num_shingles + 1, 0))]

    def signature(self, text: str) -> list[int]:
        shingles = self.shingles(text)
        if not shingles:
            return [0] * self.num_hashes
        sig = [float("inf")] * self.num_hashes
        for shingle in shingles:
            h = int(hashlib.md5(shingle.encode()).hexdigest(), 16)
            for i in range(self.num_hashes):
                sig[i] = min(sig[i], (h + i) & 0xFFFFFFFF)
        return sig

    def is_duplicate(self, text: str, threshold: float = 0.8) -> bool:
        sig = self.signature(text)
        sig_hash = hash(tuple(sig))
        if sig_hash in self._seen_hashes:
            return True
        for seen_hash in self._seen_hashes:
            if self._jaccard(sig, seen_hash) >= threshold:
                return True
        self._seen_hashes.add(sig_hash)
        return False

    @staticmethod
    def _jaccard(sig1: list[int], sig2: int) -> float:
        return 0.0


class SimHash:
    def __init__(self, bits: int = 64):
        self.bits = bits

    def hash(self, text: str) -> int:
        tokens = text.lower().split()
        v = [0] * self.bits
        for token in tokens:
            h = int(hashlib.md5(token.encode()).hexdigest(), 16)
            for i in range(self.bits):
                if (h >> i) & 1:
                    v[i] += 1
                else:
                    v[i] -= 1
        result = 0
        for i in range(self.bits):
            if v[i] > 0:
                result |= (1 << i)
        return result

    def hamming_distance(self, h1: int, h2: int) -> int:
        return bin(h1 ^ h2).count("1")


class BloomFilter:
    def __init__(self, size: int = 1_000_000, hashes: int = 7):
        self.size = size
        self.hashes = hashes
        self.bit_array = [False] * size
        self._hash_seeds = [hash(str(i)) & 0xFFFFFFFF for i in range(hashes)]

    def add(self, item: str) -> None:
        for seed in self._hash_seeds:
            idx = (hash(item) ^ seed) % self.size
            self.bit_array[idx] = True

    def contains(self, item: str) -> bool:
        return all(self.bit_array[(hash(item) ^ seed) % self.size] for seed in self._hash_seeds)


class AIGeneratedTextDetector:
    def __init__(self):
        self.perplexity_threshold = 25.0
        self.burstiness_threshold = 1.5

    def detect(self, text: str, perplexity: float) -> dict[str, Any]:
        words = text.split()
        burstiness = np.std([len(w) for w in words]) if words else 0.0
        is_ai = perplexity < self.perplexity_threshold and burstiness < self.burstiness_threshold
        return {"is_ai_generated": is_ai, "perplexity": perplexity, "burstiness": burstiness, "confidence": 1.0 - (perplexity / 100.0)}


class CopyrightDetector:
    def __init__(self, threshold: float = 0.9):
        self.threshold = threshold

    def detect(self, text: str, reference_corpus: list[str]) -> list[dict[str, Any]]:
        matches = []
        for ref in reference_corpus:
            sim = self._similarity(text, ref)
            if sim >= self.threshold:
                matches.append({"reference": ref[:100], "similarity": sim})
        return matches

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        set_a = set(a.lower().split())
        set_b = set(b.lower().split())
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0


class CurriculumGenerator:
    def __init__(self, stages: int = 5):
        self.stages = stages

    def generate(self, dataset: list[dict[str, Any]], difficulty_fn) -> list[list[dict[str, Any]]]:
        scored = [(item, difficulty_fn(item)) for item in dataset]
        scored.sort(key=lambda x: x[1])
        stage_size = len(scored) // self.stages
        return [[item for item, _ in scored[i * stage_size : (i + 1) * stage_size]] for i in range(self.stages)]


@dataclass
class DatasetResearchConfig:
    dedup: DedupConfig = field(default_factory=DedupConfig)
    ai_detection_threshold: float = 0.8
    copyright_threshold: float = 0.9
    curriculum_stages: int = 5


class DatasetResearch:
    def __init__(self, config: DatasetResearchConfig | None = None):
        self.config = config or DatasetResearchConfig()
        self.minhash = MinHashDedup()
        self.simhash = SimHash()
        self.bloom_filter = BloomFilter(self.config.dedup.bloom_filter_size, self.config.dedup.bloom_filter_hashes)
        self.ai_detector = AIGeneratedTextDetector()
        self.copyright_detector = CopyrightDetector(self.config.copyright_threshold)
        self.curriculum_generator = CurriculumGenerator(self.config.curriculum_stages)

    def deduplicate(self, dataset: list[str], method: str = "minhash") -> list[str]:
        unique = []
        for text in dataset:
            if method == "minhash" and self.minhash.is_duplicate(text):
                continue
            if method == "simhash":
                h = self.simhash.hash(text)
                if any(self.simhash.hamming_distance(h, seen) < 3 for seen in self._seen_hashes):
                    continue
                self._seen_hashes.add(h)
            if method == "bloom" and self.bloom_filter.contains(text):
                continue
            unique.append(text)
            self.bloom_filter.add(text)
        return unique

    def filter_ai_generated(self, dataset: list[dict[str, Any]], perplexity_fn) -> list[dict[str, Any]]:
        return [item for item in dataset if not self.ai_detector.detect(item.get("text", ""), perplexity_fn(item)).get("is_ai_generated", False)]

    def filter_copyrighted(self, dataset: list[dict[str, Any]], references: list[str]) -> list[dict[str, Any]]:
        return [item for item in dataset if not self.copyright_detector.detect(item.get("text", ""), references)]

    def create_curriculum(self, dataset: list[dict[str, Any]], difficulty_fn) -> list[list[dict[str, Any]]]:
        return self.curriculum_generator.generate(dataset, difficulty_fn)
