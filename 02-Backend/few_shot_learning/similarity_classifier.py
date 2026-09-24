import math
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

from .episode_sampler import Episode


def _vec_norm(v: List[float]) -> float:
    return math.sqrt(sum(x * x for x in v))


def _vec_dot(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _mat_mul(a: List[List[float]], b: List[List[float]]) -> List[List[float]]:
    cols_a = len(a[0]) if a else 0
    cols_b = len(b[0]) if b else 0
    return [
        [sum(a[i][k] * b[k][j] for k in range(cols_a)) for j in range(cols_b)]
        for i in range(len(a))
    ]


def _mat_inv(m: List[List[float]]) -> List[List[float]]:
    n = len(m)
    aug = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(m)]
    for i in range(n):
        max_row = max(range(i, n), key=lambda r: abs(aug[r][i]))
        aug[i], aug[max_row] = aug[max_row], aug[i]
        if abs(aug[i][i]) < 1e-12:
            raise ValueError("Singular matrix")
        pivot = aug[i][i]
        for j in range(2 * n):
            aug[i][j] /= pivot
        for k in range(n):
            if k == i:
                continue
            factor = aug[k][i]
            for j in range(2 * n):
                aug[k][j] -= factor * aug[i][j]
    return [row[n:] for row in aug]


class SimilarityClassifier(ABC):
    @abstractmethod
    def fit(self, support_x: List[List[float]], support_y: List[int]) -> None:
        pass

    @abstractmethod
    def predict(self, query_x: List[List[float]]) -> List[int]:
        pass

    def score(self, query_x: List[List[float]], query_y: List[int]) -> Dict[str, Any]:
        preds = self.predict(query_x)
        correct = sum(1 for p, y in zip(preds, query_y) if p == y)
        accuracy = correct / len(query_y) if query_y else 0.0
        return {"accuracy": accuracy, "predictions": preds}


class CosineSimilarityClassifier(SimilarityClassifier):
    def __init__(self):
        self.support_emb: Optional[List[List[float]]] = None
        self.support_y: Optional[List[int]] = None

    def fit(self, support_x: List[List[float]], support_y: List[int]) -> None:
        self.support_emb = [[v / _vec_norm(row) for v in row] for row in support_x]
        self.support_y = list(support_y)

    def predict(self, query_x: List[List[float]]) -> List[int]:
        if self.support_emb is None:
            return [0] * len(query_x)
        query_emb = [[v / _vec_norm(row) for v in row] for row in query_x]
        sims = [[_vec_dot(q, s) for s in self.support_emb] for q in query_emb]
        preds = []
        for row in sims:
            best = max(range(len(row)), key=row.__getitem__)
            preds.append(self.support_y[best])
        return preds


class EuclideanSimilarityClassifier(SimilarityClassifier):
    def __init__(self):
        self.support_emb: Optional[List[List[float]]] = None
        self.support_y: Optional[List[int]] = None

    def fit(self, support_x: List[List[float]], support_y: List[int]) -> None:
        self.support_emb = [list(row) for row in support_x]
        self.support_y = list(support_y)

    def predict(self, query_x: List[List[float]]) -> List[int]:
        if self.support_emb is None:
            return [0] * len(query_x)
        preds = []
        for q in query_x:
            dists = [sum((a - b) ** 2 for a, b in zip(q, s)) for s in self.support_emb]
            best = min(range(len(dists)), key=dists.__getitem__)
            preds.append(self.support_y[best])
        return preds


class MahalanobisSimilarityClassifier(SimilarityClassifier):
    def __init__(self, reg: float = 1e-4):
        self.reg = reg
        self.class_cov: Dict[int, List[List[float]]] = {}
        self.class_means: Dict[int, List[float]] = {}
        self.classes: List[int] = []

    def _col_mean(self, rows: List[List[float]]) -> List[float]:
        if not rows:
            return []
        n_cols = len(rows[0])
        return [sum(r[c] for r in rows) / len(rows) for c in range(n_cols)]

    def _cov(self, rows: List[List[float]], mean: List[float]) -> List[List[float]]:
        n = len(rows)
        n_cols = len(rows[0])
        cov = [[0.0] * n_cols for _ in range(n_cols)]
        for r in rows:
            for i in range(n_cols):
                for j in range(n_cols):
                    cov[i][j] += (r[i] - mean[i]) * (r[j] - mean[j])
        for i in range(n_cols):
            for j in range(n_cols):
                cov[i][j] /= max(n - 1, 1)
        return cov

    def fit(self, support_x: List[List[float]], support_y: List[int]) -> None:
        self.classes = sorted(set(support_y))
        for cls in self.classes:
            rows = [row for row, label in zip(support_x, support_y) if label == cls]
            mean = self._col_mean(rows)
            cov = self._cov(rows, mean)
            n_cols = len(mean)
            for i in range(n_cols):
                cov[i][i] += self.reg
            self.class_means[int(cls)] = mean
            self.class_cov[int(cls)] = cov

    def predict(self, query_x: List[List[float]]) -> List[int]:
        if not self.classes:
            return [0] * len(query_x)
        results = []
        for q in query_x:
            q_dists = []
            for cls in self.classes:
                mean = self.class_means[cls]
                cov = self.class_cov[cls]
                diff = [qi - mi for qi, mi in zip(q, mean)]
                try:
                    cov_inv = _mat_inv(cov)
                    md = sum(
                        sum(
                            diff[i] * cov_inv[i][j] * diff[j]
                            for j in range(len(diff))
                        )
                        for i in range(len(diff))
                    )
                except ValueError:
                    md = sum(d * d for d in diff)
                q_dists.append(md)
            best = min(range(len(q_dists)), key=q_dists.__getitem__)
            results.append(self.classes[best])
        return results


class PairwiseSimilarityClassifier(SimilarityClassifier):
    def __init__(self):
        self.support_emb: Optional[List[List[float]]] = None
        self.support_y: Optional[List[int]] = None

    def fit(self, support_x: List[List[float]], support_y: List[int]) -> None:
        self.support_emb = [list(row) for row in support_x]
        self.support_y = list(support_y)

    def predict(self, query_x: List[List[float]]) -> List[int]:
        if self.support_emb is None:
            return [0] * len(query_x)
        preds = []
        for q in query_x:
            sims = [_vec_dot(q, s) for s in self.support_emb]
            best = max(range(len(sims)), key=sims.__getitem__)
            preds.append(self.support_y[best])
        return preds
