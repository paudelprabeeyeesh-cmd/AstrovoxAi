from __future__ import annotations

import hashlib
import logging
import math
import os
import random
import secrets
import string
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MembershipResult:
    is_member: bool
    confidence: float
    risk_score: float
    details: dict[str, Any] = field(default_factory=dict)


class PrivacyAuditor:
    def __init__(self, sample_size: int = 1000) -> None:
        self.sample_size = sample_size
        self.audit_log: list[dict[str, Any]] = []

    def audit(self, model_id: str, member_samples: list[str], non_member_samples: list[str]) -> dict[str, Any]:
        member_entropy = self._compute_entropy(member_samples)
        non_member_entropy = self._compute_entropy(non_member_samples)
        leakage = abs(member_entropy - non_member_entropy)
        result = {"model_id": model_id, "member_entropy": member_entropy, "non_member_entropy": non_member_entropy, "leakage_score": leakage, "audit_timestamp": time.time(), "passed": leakage < 0.5}
        self.audit_log.append(result)
        return result

    def _compute_entropy(self, samples: list[str]) -> float:
        if not samples:
            return 0.0
        lengths = [len(s) for s in samples]
        mean_len = sum(lengths) / len(lengths)
        variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths) if lengths else 0.0
        return math.log(variance + 1.0)


@dataclass
class DifferentialPrivacyConfig:
    epsilon: float = 1.0
    delta: float = 1e-5
    noise_scale: float = 1.0
    clip_norm: float = 1.0


class DifferentialPrivacyMechanism:
    def __init__(self, config: DifferentialPrivacyConfig | None = None) -> None:
        self.config = config or DifferentialPrivacyConfig()
        self.epsilon_spent = 0.0
        self.query_count = 0

    def add_noise(self, value: float) -> float:
        if self.epsilon_spent >= self.config.epsilon:
            raise RuntimeError("Privacy budget exhausted")
        scale = self.config.noise_scale * self.config.clip_norm / self.config.epsilon
        noise = random.gauss(0, scale)
        self.epsilon_spent += 1.0 / self.config.noise_scale
        self.query_count += 1
        return value + noise

    def add_noise_vector(self, values: list[float]) -> list[float]:
        return [self.add_noise(v) for v in values]

    def remaining_budget(self) -> float:
        return max(0.0, self.config.epsilon - self.epsilon_spent)

    def reset_budget(self) -> None:
        self.epsilon_spent = 0.0
        self.query_count = 0


@dataclass
class PerturbationConfig:
    noise_scale: float = 0.1
    perturbation_probability: float = 0.2
    seed: int | None = None


class OutputPerturbator:
    def __init__(self, config: PerturbationConfig | None = None) -> None:
        self.config = config or PerturbationConfig()
        self._rng = random.Random(self.config.seed)

    def perturb_text(self, text: str) -> str:
        if not text or self._rng.random() > self.config.perturbation_probability:
            return text
        chars = list(text)
        for idx in range(len(chars)):
            if chars[idx].isalpha() and self._rng.random() < self.config.noise_scale:
                chars[idx] = self._rng.choice(string.ascii_letters)
        return "".join(chars)

    def perturb_embeddings(self, embeddings: list[float]) -> list[float]:
        scale = self.config.noise_scale * math.sqrt(len(embeddings)) if embeddings else 0.0
        return [v + self._rng.gauss(0, scale) for v in embeddings]
