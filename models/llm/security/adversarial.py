from __future__ import annotations

import hashlib
import logging
import math
import os
import random
import re
import secrets
import string
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PerturbationResult:
    is_adversarial: bool
    perturbation_score: float
    original_confidence: float
    perturbed_confidence: float
    details: dict[str, Any] = field(default_factory=dict)


class InputPerturbationDetector:
    def __init__(self, threshold: float = 0.3) -> None:
        self.threshold = threshold

    def detect(self, original: str, candidate: str) -> PerturbationResult:
        if not isinstance(original, str) or not isinstance(candidate, str):
            return PerturbationResult(is_adversarial=True, perturbation_score=1.0, original_confidence=0.0, perturbed_confidence=0.0, details={"error": "invalid_input_type"})
        orig_tokens = original.split()
        cand_tokens = candidate.split()
        length_diff = abs(len(orig_tokens) - len(cand_tokens)) / max(len(orig_tokens), 1)
        levenshtein = self._levenshtein(original, candidate)
        max_len = max(len(original), len(candidate), 1)
        normalized_dist = levenshtein / max_len
        special_char_ratio_orig = sum(1 for c in original if not c.isalnum() and c not in " \t\n\r") / max(len(original), 1)
        special_char_ratio_cand = sum(1 for c in candidate if not c.isalnum() and c not in " \t\n\r") / max(len(candidate), 1)
        special_char_delta = abs(special_char_ratio_orig - special_char_ratio_cand)
        score = min((normalized_dist * 0.5) + (special_char_delta * 2.0) + (length_diff * 0.3), 1.0)
        return PerturbationResult(is_adversarial=score > self.threshold, perturbation_score=score, original_confidence=1.0 - score, perturbed_confidence=1.0 - score * 0.5, details={"levenshtein": levenshtein, "length_delta": length_diff, "special_char_delta": special_char_delta})

    def _levenshtein(self, a: str, b: str) -> int:
        m, n = len(a), len(b)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                cost = 0 if a[i - 1] == b[j - 1] else 1
                dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)
        return dp[m][n]


class RobustnessTester:
    def __init__(self) -> None:
        self.test_results: list[dict[str, Any]] = []

    def test_synonym_replacement(self, text: str, max_replacements: int = 5) -> str:
        synonyms = {"fast": "quick", "slow": "sluggish", "good": "great", "bad": "poor", "big": "large", "small": "tiny", "happy": "glad", "sad": "unhappy"}
        words = text.split()
        replaced = 0
        for idx in range(len(words)):
            lower = words[idx].lower()
            if lower in synonyms and replaced < max_replacements:
                words[idx] = synonyms[lower]
                replaced += 1
        return " ".join(words)

    def test_character_noise(self, text: str, noise_ratio: float = 0.05) -> str:
        chars = list(text)
        swaps = 0
        target = int(len(chars) * noise_ratio)
        for idx in range(len(chars) - 1):
            if swaps >= target:
                break
            if chars[idx].isalpha() and chars[idx + 1].isalpha():
                chars[idx], chars[idx + 1] = chars[idx + 1], chars[idx]
                swaps += 1
        return "".join(chars)

    def test_unicode_homoglyphs(self, text: str) -> str:
        homoglyphs = {"a": "а", "e": "е", "o": "о", "p": "р", "c": "с", "x": "х", "y": "у", "i": "і", "j": "ј", "s": "ѕ"}
        result = []
        for char in text:
            lower = char.lower()
            if lower in homoglyphs and random.random() < 0.1:
                replacement = homoglyphs[lower]
                result.append(replacement if char.islower() else replacement.upper())
            else:
                result.append(char)
        return "".join(result)

    def run_suite(self, text: str, classifier: Any) -> list[dict[str, Any]]:
        tests = [("original", text), ("synonym", self.test_synonym_replacement(text)), ("char_noise", self.test_character_noise(text)), ("homoglyph", self.test_unicode_homoglyphs(text))]
        results = []
        for name, variant in tests:
            try:
                confidence = classifier(variant) if callable(classifier) else 0.5
            except Exception:
                confidence = 0.5
            passed = confidence >= 0.5
            results.append({"test": name, "passed": passed, "confidence": confidence, "variant_preview": variant[:100]})
            self.test_results.append({"test": name, "passed": passed, "confidence": confidence})
        return results


class DefensiveMechanism:
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    def input_transformation(self, text: str) -> str:
        cleaned = text.lower()
        cleaned = re.sub(r"[^\x00-\x7f]+", "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def defensive_distillation(self, logits: list[float], temperature: float = 2.0) -> list[float]:
        if not logits:
            return []
        max_logit = max(logits)
        exps = [math.exp((l - max_logit) / temperature) for l in logits]
        total = sum(exps)
        return [e / total for e in exps] if total > 0 else [0.0] * len(logits)

    def adversarial_training_simulation(self, text: str, num_variants: int = 3) -> list[str]:
        variants = [text]
        for _ in range(num_variants - 1):
            noisy = list(text)
            for idx in random.sample(range(len(noisy)), min(len(noisy) // 10, 5)):
                if noisy[idx].isalpha():
                    noisy[idx] = random.choice(string.ascii_letters)
            variants.append("".join(noisy))
        return variants
