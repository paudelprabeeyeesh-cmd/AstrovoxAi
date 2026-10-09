import numpy as np
from dataclasses import dataclass
from typing import Tuple, Dict, Any, Optional


@dataclass
class ManifoldConfig:
    input_dim: int
    n_components: int = 2
    n_neighbors: int = 5
    n_iter: int = 200
    learning_rate: float = 0.01


class ManifoldLearner:
    def __init__(self, config: ManifoldConfig):
        self.config = config
        self.embedding: Optional[np.ndarray] = None
        self.loss_history: list = []

    def _pairwise_distances(self, x: np.ndarray) -> np.ndarray:
        xx = np.sum(x ** 2, axis=1, keepdims=True)
        return np.maximum(xx + xx.T - 2.0 * (x @ x.T), 0.0)

    def _affinity_matrix(self, distances: np.ndarray) -> np.ndarray:
        n = distances.shape[0]
        k = min(self.config.n_neighbors, n - 1)
        A = np.zeros((n, n), dtype=np.float64)
        for i in range(n):
            idx = np.argsort(distances[i])[1 : k + 1]
            A[i, idx] = 1.0
        A = np.maximum(A, A.T)
        D = np.diag(np.sum(A, axis=1))
        L = D - A
        return L, A

    def _spectral_embedding(self, L: np.ndarray, n_components: int) -> np.ndarray:
        vals, vecs = np.linalg.eigh(L)
        idx = np.argsort(vals)
        vals = vals[idx]
        vecs = vecs[:, idx]
        components = vecs[:, 1 : n_components + 1]
        return components

    def fit_transform(self, x: np.ndarray) -> np.ndarray:
        n = x.shape[0]
        distances = self._pairwise_distances(x)
        L, _ = self._affinity_matrix(distances)
        embedding = self._spectral_embedding(L, self.config.n_components)
        self.embedding = embedding
        return embedding

    def fit(self, x: np.ndarray) -> "ManifoldLearner":
        self.fit_transform(x)
        return self

    def transform(self, x: np.ndarray) -> np.ndarray:
        if self.embedding is None:
            raise RuntimeError("ManifoldLearner has not been fitted yet.")
        return self.embedding[: x.shape[0]]

    def reconstruction_error(self, x: np.ndarray, embedding: Optional[np.ndarray] = None) -> float:
        if embedding is None:
            embedding = self.embedding
        if embedding is None:
            raise RuntimeError("ManifoldLearner has not been fitted yet.")
        x_center = x - np.mean(x, axis=0, keepdims=True)
        emb_center = embedding - np.mean(embedding, axis=0, keepdims=True)
        _, _, v = np.linalg.svd(x_center, full_matrices=False)
        projection = emb_center @ v[: self.config.n_components].T
        recon = projection @ v[: self.config.n_components]
        return float(np.mean((x_center - recon) ** 2))

    def get_report(self) -> Dict[str, Any]:
        return {
            "n_components": self.config.n_components,
            "n_neighbors": self.config.n_neighbors,
            "fitted": self.embedding is not None,
            "embedding_shape": list(self.embedding.shape) if self.embedding is not None else None,
        }
