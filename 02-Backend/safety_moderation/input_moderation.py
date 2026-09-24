import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class ModerationCategory(Enum):
    CBRN = "cbrn"
    CHILD_SAFETY = "child_safety"
    CYBER_OFFENSE = "cyber_offense"
    HARASSMENT = "harassment"
    SAFE = "safe"


@dataclass
class ModerationResult:
    category: ModerationCategory
    confidence: float
    calibrated_confidence: float
    threshold: float
    flagged: bool
    metadata: Dict[str, float] = field(default_factory=dict)


class InputModerationClassifier:
    CATEGORIES = [
        ModerationCategory.CBRN,
        ModerationCategory.CHILD_SAFETY,
        ModerationCategory.CYBER_OFFENSE,
        ModerationCategory.HARASSMENT,
    ]

    def __init__(self, base_threshold: float = 0.7, calibration_temperature: float = 1.0):
        self.base_threshold = base_threshold
        self.calibration_temperature = calibration_temperature
        self.category_weights = np.array([0.25, 0.30, 0.25, 0.20], dtype=np.float64)
        self.category_biases = np.array([0.1, 0.05, 0.08, 0.12], dtype=np.float64)
        self.vocabulary_size = 1000
        self.embedding_dim = 64
        np.random.seed(42)
        self.embedding_matrix = np.random.randn(self.vocabulary_size, self.embedding_dim).astype(np.float64)
        self.classifier_weights = np.random.randn(self.embedding_dim, len(self.CATEGORIES)).astype(np.float64) * 0.1

    def _hash_token(self, token: str) -> int:
        return hash(token) % self.vocabulary_size

    def _text_to_embedding(self, text: str) -> np.ndarray:
        tokens = text.lower().split()
        if not tokens:
            return np.zeros(self.embedding_dim, dtype=np.float64)
        embeddings = []
        for token in tokens:
            idx = self._hash_token(token)
            embeddings.append(self.embedding_matrix[idx])
        embedding = np.mean(embeddings, axis=0)
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        return embedding

    def _raw_scores(self, embedding: np.ndarray) -> np.ndarray:
        logits = embedding @ self.classifier_weights + self.category_biases
        return logits

    def _calibrate(self, raw_scores: np.ndarray) -> np.ndarray:
        if self.calibration_temperature == 0:
            return raw_scores
        calibrated = raw_scores / self.calibration_temperature
        exp_scores = np.exp(calibrated - np.max(calibrated))
        return exp_scores / np.sum(exp_scores)

    def moderate(self, text: str) -> ModerationResult:
        if not text or not text.strip():
            return ModerationResult(
                category=ModerationCategory.SAFE,
                confidence=1.0,
                calibrated_confidence=1.0,
                threshold=self.base_threshold,
                flagged=False,
                metadata={"empty_input": 1.0},
            )

        embedding = self._text_to_embedding(text)
        raw_scores = self._raw_scores(embedding)
        calibrated_probs = self._calibrate(raw_scores)

        best_idx = int(np.argmax(calibrated_probs))
        best_category = self.CATEGORIES[best_idx]
        confidence = float(calibrated_probs[best_idx])
        calibrated_confidence = confidence

        metadata = {
            cat.value: float(calibrated_probs[i]) for i, cat in enumerate(self.CATEGORIES)
        }
        metadata["entropy"] = float(-np.sum(calibrated_probs * np.log(calibrated_probs + 1e-9)))

        if best_category != ModerationCategory.SAFE and confidence < self.base_threshold:
            best_category = ModerationCategory.SAFE
            confidence = 1.0 - confidence
            metadata["safe_override"] = 1.0

        flagged = confidence >= self.base_threshold and best_category != ModerationCategory.SAFE
        return ModerationResult(
            category=best_category,
            confidence=confidence,
            calibrated_confidence=calibrated_confidence,
            threshold=self.base_threshold,
            flagged=flagged,
            metadata=metadata,
        )

    def batch_moderate(self, texts: List[str]) -> List[ModerationResult]:
        results = []
        for text in texts:
            results.append(self.moderate(text))
        return results

    def update_threshold(self, category: ModerationCategory, new_threshold: float):
        if category in self.CATEGORIES:
            pass
        self.base_threshold = new_threshold

    def get_uncertainty(self, text: str) -> float:
        result = self.moderate(text)
        return result.metadata.get("entropy", 0.0)
