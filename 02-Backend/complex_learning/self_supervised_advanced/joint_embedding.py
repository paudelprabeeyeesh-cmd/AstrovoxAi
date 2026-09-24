from dataclasses import dataclass, field
from math import exp, sqrt
from random import sample, seed
from typing import List, Optional, Sequence, Tuple


@dataclass
class JointEmbeddingConfig:
    input_dim: int = 16
    embed_dim: int = 8
    temperature: float = 0.07
    seed: Optional[int] = None


@dataclass
class JointEmbedding:
    config: JointEmbeddingConfig = field(default_factory=JointEmbeddingConfig)
    _w: List[List[float]] = field(init=False, default_factory=list)
    _b: List[float] = field(init=False, default_factory=list)

    def __post_init__(self) -> None:
        if self.config.seed is not None:
            seed(self.config.seed)
        d_in = self.config.input_dim
        d_out = self.config.embed_dim
        self._w = [[(_small_random()) for _ in range(d_out)] for _ in range(d_in)]
        self._b = [0.0] * d_out

    @staticmethod
    def _norm(v: List[float]) -> float:
        return sqrt(sum(x * x for x in v))

    @staticmethod
    def _normalize(v: List[float]) -> List[float]:
        n = JointEmbedding._norm(v)
        if n == 0.0:
            return [0.0] * len(v)
        return [x / n for x in v]

    @staticmethod
    def _matmul(a: List[List[float]], b: List[List[float]]) -> List[List[float]]:
        m = len(a)
        n = len(b[0])
        p = len(b)
        return [[sum(a[i][k] * b[k][j] for k in range(p)) for j in range(n)] for i in range(m)]

    @staticmethod
    def _matmul_vec(a: List[List[float]], b: List[float]) -> List[float]:
        return [sum(a[i][j] * b[j] for j in range(len(b))) for i in range(len(a))]

    def _add_bias(self, a: List[List[float]]) -> List[List[float]]:
        return [[a[i][j] + self._b[j] for j in range(len(a[0]))] for i in range(len(a))]

    def embed(self, x: List[List[float]]) -> List[List[float]]:
        h = [self._matmul_vec(self._w, row) for row in x]
        out = self._add_bias(h)
        return [self._normalize(row) for row in out]

    def embed_single(self, x: List[float]) -> List[float]:
        h = self._matmul_vec(self._w, x)
        h = [h[i] + self._b[i] for i in range(len(h))]
        return self._normalize(h)

    def compute_similarity(self, a: List[float], b: List[float]) -> float:
        return sum(ai * bi for ai, bi in zip(a, b))

    def temperature_scaled(self, similarity: float) -> float:
        return similarity / self.config.temperature

    def nce_loss(self, positive: List[float], negatives: List[List[float]]) -> float:
        pos = self.compute_similarity(positive, positive)
        logits = [pos]
        for neg in negatives:
            logits.append(self.compute_similarity(positive, neg))
        logits = [l / self.config.temperature for l in logits]
        max_logit = max(logits)
        exp_logits = [exp(l - max_logit) for l in logits]
        total = sum(exp_logits)
        loss = -logits[0] + total
        return loss / total if total != 0 else 0.0

    def contrastive_loss(self, a: List[float], b: List[float], negatives: List[List[float]]) -> float:
        return self.nce_loss(a, [b] + negatives)

    def joint_embedding_step(self, a: List[List[float]], b: List[List[float]]) -> float:
        za = [self.embed_single(row) for row in a]
        zb = [self.embed_single(row) for row in b]
        loss = 0.0
        for i in range(len(za)):
            neg = za[:i] + za[i+1:]
            loss += self.nce_loss(za[i], [zb[i]] + neg)
        return loss / len(za)

    def predict(self, x: List[float], memory: List[List[float]]) -> int:
        z = self.embed_single(x)
        best = -1.0
        best_idx = -1
        for i, mem in enumerate(memory):
            mem_z = self.embed_single(mem)
            s = self.compute_similarity(z, mem_z)
            if s > best:
                best = s
                best_idx = i
        return best_idx


def _small_random() -> float:
    return (sample(range(100), 1)[0] / 10000.0) - 0.005
