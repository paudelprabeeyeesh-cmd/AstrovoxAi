from __future__ import annotations

import hashlib
import logging
import math
import os
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DataSample:
    id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    checksum: str = ""

    def __post_init__(self) -> None:
        if not self.checksum:
            self.checksum = hashlib.sha256(self.text.encode("utf-8")).hexdigest()[:16]


@dataclass
class PoisoningResult:
    is_clean: bool
    outlier_count: int
    duplicate_count: int
    integrity_issues: list[str]
    trust_score: float


class TrainingDataValidator:
    def __init__(self, max_duplicates: int = 3, outlier_z_threshold: float = 3.0) -> None:
        self.max_duplicates = max_duplicates
        self.outlier_z_threshold = outlier_z_threshold
        self.seen_checksums: dict[str, int] = {}

    def validate_samples(self, samples: list[DataSample]) -> PoisoningResult:
        integrity_issues: list[str] = []
        outlier_count = 0
        duplicate_count = 0
        self.seen_checksums.clear()
        lengths = [len(s.text.split()) for s in samples]
        if len(lengths) >= 3:
            mean_len = statistics.mean(lengths)
            stdev_len = statistics.stdev(lengths) if len(lengths) > 1 else 0.0
        else:
            mean_len = statistics.mean(lengths) if lengths else 0.0
            stdev_len = 0.0
        for sample in samples:
            if not sample.text or len(sample.text.strip()) < 3:
                integrity_issues.append(f"Sample {sample.id} is too short or empty")
                outlier_count += 1
                continue
            expected_checksum = hashlib.sha256(sample.text.encode("utf-8")).hexdigest()[:16]
            if sample.checksum != expected_checksum:
                integrity_issues.append(f"Sample {sample.id} checksum mismatch")
            if sample.id in self.seen_checksums:
                self.seen_checksums[sample.id] += 1
            else:
                self.seen_checksums[sample.id] = 1
            if stdev_len > 0:
                z_score = (len(sample.text.split()) - mean_len) / stdev_len
                if abs(z_score) > self.outlier_z_threshold:
                    integrity_issues.append(f"Sample {sample.id} is a statistical outlier (z={z_score:.2f})")
                    outlier_count += 1
        for sample_id, count in self.seen_checksums.items():
            if count > self.max_duplicates:
                duplicate_count += count - self.max_duplicates
                integrity_issues.append(f"Sample {sample_id} appears {count} times (max {self.max_duplicates})")
        # Duplicates are counted by content, not by id: the same text
        # submitted under two different ids is still a duplicate, and
        # keying on the id alone would miss exactly that case.
        content_counts: dict[str, int] = {}
        for sample in samples:
            if sample.text and len(sample.text.strip()) >= 3:
                key = hashlib.sha256(sample.text.encode("utf-8")).hexdigest()[:16]
                content_counts[key] = content_counts.get(key, 0) + 1
        for key, count in content_counts.items():
            if count > self.max_duplicates:
                extra = count - self.max_duplicates
                duplicate_count += extra
                integrity_issues.append(
                    f"Identical text appears {count} times (max {self.max_duplicates})"
                )
        total_samples = len(samples) if samples else 1
        penalty = min((outlier_count + duplicate_count + len(integrity_issues)) / total_samples, 1.0)
        trust_score = max(0.0, 1.0 - penalty)
        return PoisoningResult(is_clean=len(integrity_issues) == 0, outlier_count=outlier_count, duplicate_count=duplicate_count, integrity_issues=integrity_issues, trust_score=trust_score)


class OutlierDetector:
    def __init__(self, z_threshold: float = 3.0) -> None:
        self.z_threshold = z_threshold

    def detect(self, values: list[float]) -> list[int]:
        if len(values) < 3:
            return []
        mean = statistics.mean(values)
        stdev = statistics.stdev(values) if len(values) > 1 else 0.0
        if stdev == 0:
            return []
        outliers: list[int] = []
        for idx, value in enumerate(values):
            z_score = (value - mean) / stdev
            if abs(z_score) > self.z_threshold:
                outliers.append(idx)
        return outliers


class DataIntegrityChecker:
    def verify_checksum(self, data: str, expected: str) -> bool:
        actual = hashlib.sha256(data.encode("utf-8")).hexdigest()[:16]
        return actual == expected

    def compute_checksum(self, data: str) -> str:
        return hashlib.sha256(data.encode("utf-8")).hexdigest()[:16]

    def verify_batch(self, samples: list[DataSample]) -> list[str]:
        issues: list[str] = []
        for sample in samples:
            if not self.verify_checksum(sample.text, sample.checksum):
                issues.append(f"Checksum mismatch for sample {sample.id}")
        return issues
