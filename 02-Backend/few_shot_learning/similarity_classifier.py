import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
from .episode_sampler import Episode


class SimilarityClassifier(ABC):
    @abstractmethod
    def fit(self, support_x: np.ndarray, support_y: np.ndarray) -> None:
        pass

    @abstractmethod
    def predict(self, query_x: np.ndarray) -> np.ndarray:
        pass

    def score(self, query_x: np.ndarray, query_y: np.ndarray) -> Dict[str, Any]:
        preds = self.predict(query_x)
        accuracy = float(np.mean(preds == query_y.astype(int)))
        return {"accuracy": accuracy, "predictions": preds}


class CosineSimilarityClassifier(SimilarityClassifier):
    def __init__(self):
        self.support_emb: Optional[np.ndarray] = None
        self.support_y: Optional[np.ndarray] = None

    def fit(self, support_x: np.ndarray, support_y: np.ndarray) -> None:
        norms = np.linalg.norm(support_x, axis=1, keepdims=True)
        self.support_emb = support_x / np.clip(norms, 1e-12, None)
        self.support_y = support_y.astype(int)

    def predict(self, query_x: np.ndarray) -> np.ndarray:
        if self.support_emb is None:
            return np.zeros(len(query_x), dtype=int)
        query_norms = np.linalg.norm(query_x, axis=1, keepdims=True)
        query_emb = query_x / np.clip(query_norms, 1e-12, None)
        sims = query_emb @ self.support_emb.T
        closest = np.argmax(sims, axis=1)
        return self.support_y[closest]


class EuclideanSimilarityClassifier(SimilarityClassifier):
    def __init__(self):
        self.support_emb: Optional[np.ndarray] = None
        self.support_y: Optional[np.ndarray] = None

    def fit(self, support_x: np.ndarray, support_y: np.ndarray) -> None:
        self.support_emb = support_x.astype(np.float64)
        self.support_y = support_y.astype(int)

    def predict(self, query_x: np.ndarray) -> np.ndarray:
        if self.support_emb is None:
            return np.zeros(len(query_x), dtype=int)
        dists = np.sum((query_x[:, None, :] - self.support_emb[None, :, :]) ** 2, axis=2)
        closest = np.argmin(dists, axis=1)
        return self.support_y[closest]


class MahalanobisSimilarityClassifier(SimilarityClassifier):
    def __init__(self, reg: float = 1e-4):
        self.reg = reg
        self.class_cov: Dict[int, np.ndarray] = {}
        self.class_means: Dict[int, np.ndarray] = {}
        self.classes: List[int] = []

    def fit(self, support_x: np.ndarray, support_y: np.ndarray) -> None:
        self.classes = sorted(np.unique(support_y))
        for cls in self.classes:
            mask = support_y == cls
            class_x = support_x[mask].astype(np.float64)
            mean = np.mean(class_x, axis=0)
            centered = class_x - mean
            cov = (centered.T @ centered) / max(len(class_x) - 1, 1)
            cov += self.reg * np.eye(cov.shape[0])
            self.class_means[int(cls)] = mean
            self.class_cov[int(cls)] = cov

    def predict(self, query_x: np.ndarray) -> np.ndarray:
        if not self.classes:
            return np.zeros(len(query_x), dtype=int)
        results = np.zeros((len(query_x), len(self.classes)))
        for i, cls in enumerate(self.classes):
            mean = self.class_means[cls]
            cov = self.class_cov[cls]
            diff = query_x.astype(np.float64) - mean
            try:
                cov_inv = np.linalg.inv(cov)
                results[:, i] = np.sum(diff @ cov_inv * diff, axis=1)
            except np.linalg.LinAlgError:
                results[:, i] = np.sum(diff ** 2, axis=1)
        closest = np.argmin(results, axis=1)
        return np.array([self.classes[i] for i in closest], dtype=int)


class PairwiseSimilarityClassifier(SimilarityClassifier):
    def __init__(self):
        self.support_emb: Optional[np.ndarray] = None
        self.support_y: Optional[np.ndarray] = None

    def fit(self, support_x: np.ndarray, support_y: np.ndarray) -> None:
        self.support_emb = support_x.astype(np.float64)
        self.support_y = support_y.astype(int)

    def predict(self, query_x: np.ndarray) -> np.ndarray:
        if self.support_emb is None:
            return np.zeros(len(query_x), dtype=int)
        sims = query_x @ self.support_emb.T
        closest = np.argmax(sims, axis=1)
        return self.support_y[closest]
