from dataclasses import dataclass, field
from math import sqrt
from typing import Any, Dict, List, Optional


@dataclass
class FusionResult:
    fused_embedding: List[float]
    alignment_scores: Dict[str, float]
    modality_contributions: Dict[str, float]
    metadata: Dict[str, Any] = field(default_factory=dict)


class FusionEngine:
    def __init__(self, embed_dim: int = 256):
        self.embed_dim = embed_dim
        self._rng = _Rng(42)

    def _random_matrix(self, rows: int, cols: int) -> List[List[float]]:
        return [self._rng.normal(0.0, 0.02, cols) for _ in range(rows)]

    def _matmul(self, A: List[List[float]], B: List[float]) -> List[float]:
        return [sum(A[i][j] * B[j] for j in range(len(B))) for i in range(len(A))]

    def early_fusion(
        self, text_emb: List[float], image_emb: List[float], audio_emb: Optional[List[float]] = None
    ) -> List[float]:
        concat = list(text_emb) + list(image_emb)
        if audio_emb is not None:
            concat = concat + list(audio_emb)
        W_early = self._random_matrix(len(concat), self.embed_dim)
        return [_tanh(x) for x in self._matmul(W_early, concat)]

    def late_fusion(
        self, text_emb: List[float], image_emb: List[float], audio_emb: Optional[List[float]] = None
    ) -> List[float]:
        W_late = self._random_matrix(self.embed_dim, self.embed_dim)
        text_proj = self._matmul(W_late, text_emb)
        image_proj = self._matmul(W_late, image_emb)
        modalities = [text_proj, image_proj]
        if audio_emb is not None:
            modalities.append(self._matmul(W_late, audio_emb))
        return [sum(m[i] for m in modalities) / len(modalities) for i in range(self.embed_dim)]

    def hybrid_fusion(
        self, text_emb: List[float], image_emb: List[float], audio_emb: Optional[List[float]] = None
    ) -> List[float]:
        early = self.early_fusion(text_emb, image_emb, audio_emb)
        late = self.late_fusion(text_emb, image_emb, audio_emb)
        concat = early + late
        W_hybrid = self._random_matrix(2 * self.embed_dim, self.embed_dim)
        return [_tanh(x) for x in self._matmul(W_hybrid, concat)]

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        dot = sum(ai * bi for ai, bi in zip(a, b))
        norm_a = sqrt(sum(ai * ai for ai in a))
        norm_b = sqrt(sum(bi * bi for bi in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def compute_alignment_score(self, X: List[List[float]], Y: List[List[float]]) -> float:
        scores = []
        for x in X[:10]:
            for y in Y[:10]:
                scores.append(self._cosine_similarity(x, y))
        return sum(scores) / len(scores) if scores else 0.0

    def align_modalities(self, embeddings: Dict[str, List[float]]) -> Dict[str, float]:
        keys = list(embeddings.keys())
        if len(keys) < 2:
            return {}
        aligned = {}
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                score = self.compute_alignment_score([embeddings[keys[i]]], [embeddings[keys[j]]])
                aligned[f"{keys[i]}_{keys[j]}"] = score
        return aligned

    def fuse(
        self,
        text_emb: List[float],
        image_emb: List[float],
        audio_emb: Optional[List[float]] = None,
    ) -> FusionResult:
        early = self.early_fusion(text_emb, image_emb, audio_emb)
        late = self.late_fusion(text_emb, image_emb, audio_emb)
        hybrid = self.hybrid_fusion(text_emb, image_emb, audio_emb)

        embeddings: Dict[str, List[float]] = {
            "text": text_emb,
            "image": image_emb,
            "early": early,
            "late": late,
        }
        if audio_emb is not None:
            embeddings["audio"] = audio_emb

        alignment_scores = self.align_modalities(embeddings)

        contributions = {
            "text": sqrt(sum(x * x for x in text_emb)),
            "image": sqrt(sum(x * x for x in image_emb)),
        }
        if audio_emb is not None:
            contributions["audio"] = sqrt(sum(x * x for x in audio_emb))

        return FusionResult(
            fused_embedding=hybrid,
            alignment_scores=alignment_scores,
            modality_contributions=contributions,
        )


def _tanh(x: float) -> float:
    return (2.0 / (1.0 + 2.718281828459045 ** (-2 * x))) - 1.0


class _Rng:
    def __init__(self, seed: int):
        self._state = seed & 0xFFFFFFFF

    def _next(self) -> int:
        self._state = (1103515245 * self._state + 12345) & 0xFFFFFFFF
        return self._state

    def uniform(self) -> float:
        return self._next() / 0xFFFFFFFF

    def normal(self, mu: float, sigma: float, n: int) -> List[float]:
        vals = [0.0] * n
        for i in range(n):
            u = self.uniform()
            v = self.uniform()
            z = sqrt(-2.0 * log(u)) * cos(2.0 * 3.141592653589793 * v)
            vals[i] = mu + z * sigma
        return vals
