from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List
import math


class ContentCategory(Enum):
    SAFE = "safe"
    HARMFUL = "harmful"
    SENSITIVE = "sensitive"
    UNKNOWN = "unknown"


@dataclass
class ContentModerationResult:
    category: ContentCategory
    confidence: float
    threshold: float
    flagged: bool
    details: Dict[str, float] = field(default_factory=dict)


class ContentModerator:
    CATEGORIES = [
        ContentCategory.SAFE,
        ContentCategory.HARMFUL,
        ContentCategory.SENSITIVE,
        ContentCategory.UNKNOWN,
    ]

    def __init__(self, threshold: float = 0.7):
        self.threshold = threshold
        self.vocab_size = 1000
        self.embedding_dim = 32
        self._seed = 42
        self._init_embeddings()

    def _init_embeddings(self):
        import random
        random.seed(self._seed)
        self.embedding_matrix = [[random.gauss(0, 1) for _ in range(self.embedding_dim)] for _ in range(self.vocab_size)]
        self.classifier_weights = [[random.gauss(0, 0.1) for _ in range(len(self.CATEGORIES))] for _ in range(self.embedding_dim)]
        self.category_biases = [0.1, 0.2, 0.15, 0.05]

    def _hash_token(self, token: str) -> int:
        return hash(token) % self.vocab_size

    def _text_to_embedding(self, text: str) -> List[float]:
        tokens = text.lower().split()
        if not tokens:
            return [0.0] * self.embedding_dim
        dim = self.embedding_dim
        emb = [0.0] * dim
        for token in tokens:
            idx = self._hash_token(token)
            row = self.embedding_matrix[idx]
            for i in range(dim):
                emb[i] += row[i]
        count = len(tokens)
        for i in range(dim):
            emb[i] /= count
        norm = math.sqrt(sum(x * x for x in emb))
        if norm > 0:
            for i in range(dim):
                emb[i] /= norm
        return emb

    def _raw_scores(self, embedding: List[float]) -> List[float]:
        scores = []
        for j in range(len(self.CATEGORIES)):
            s = self.category_biases[j]
            for i in range(self.embedding_dim):
                s += embedding[i] * self.classifier_weights[i][j]
            scores.append(s)
        return scores

    def _calibrate(self, raw_scores: List[float]) -> List[float]:
        max_s = max(raw_scores)
        exps = [math.exp(s - max_s) for s in raw_scores]
        total = sum(exps)
        if total == 0:
            return [1.0 / len(raw_scores)] * len(raw_scores)
        return [e / total for e in exps]

    def moderate(self, text: str) -> ContentModerationResult:
        if not text or not text.strip():
            return ContentModerationResult(
                category=ContentCategory.SAFE,
                confidence=1.0,
                threshold=self.threshold,
                flagged=False,
                details={"empty_input": 1.0},
            )

        embedding = self._text_to_embedding(text)
        raw_scores = self._raw_scores(embedding)
        calibrated = self._calibrate(raw_scores)

        best_idx = max(range(len(calibrated)), key=lambda i: calibrated[i])
        best_category = self.CATEGORIES[best_idx]
        confidence = calibrated[best_idx]

        details = {cat.value: calibrated[i] for i, cat in enumerate(self.CATEGORIES)}
        entropy = -sum(p * math.log(p + 1e-12) for p in calibrated)
        details["entropy"] = entropy

        if best_category != ContentCategory.SAFE and confidence < self.threshold:
            best_category = ContentCategory.SAFE
            confidence = 1.0 - confidence
            details["safe_override"] = 1.0

        flagged = confidence >= self.threshold and best_category != ContentCategory.SAFE
        return ContentModerationResult(
            category=best_category,
            confidence=confidence,
            threshold=self.threshold,
            flagged=flagged,
            details=details,
        )

    def batch_moderate(self, texts: List[str]) -> List[ContentModerationResult]:
        return [self.moderate(text) for text in texts]

    def update_threshold(self, new_threshold: float):
        self.threshold = new_threshold

    def get_uncertainty(self, text: str) -> float:
        result = self.moderate(text)
        return result.details.get("entropy", 0.0)
