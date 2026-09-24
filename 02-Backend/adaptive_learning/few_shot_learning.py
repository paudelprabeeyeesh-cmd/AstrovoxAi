import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass


@dataclass
class Episode:
    support_x: np.ndarray
    support_y: np.ndarray
    query_x: np.ndarray
    query_y: np.ndarray
    n_way: int = 5
    k_shot: int = 1


class PrototypicalNetworks:
    def __init__(self, embedding_dim: int = 64):
        self.embedding_dim = embedding_dim
        self.prototypes: Dict[int, np.ndarray] = {}
        self.class_encoder: Dict[int, int] = {}
        self._next_code = 0

    def _encode(self, x: np.ndarray) -> np.ndarray:
        W = np.random.randn(x.shape[1], self.embedding_dim).astype(np.float64) * 0.1
        return x @ W

    def compute_prototypes(self, support_x: np.ndarray, support_y: np.ndarray) -> Dict[int, np.ndarray]:
        prototypes: Dict[int, np.ndarray] = {}
        for cls in np.unique(support_y):
            mask = support_y == cls
            if cls not in self.class_encoder:
                self.class_encoder[int(cls)] = self._next_code
                self._next_code += 1
            embeddings = self._encode(support_x[mask])
            prototypes[int(cls)] = np.mean(embeddings, axis=0)
        return prototypes

    def classify(self, query_x: np.ndarray, prototypes: Optional[Dict[int, np.ndarray]] = None) -> np.ndarray:
        if prototypes is None:
            prototypes = self.prototypes
        if not prototypes:
            return np.zeros(len(query_x), dtype=int)
        embeddings = self._encode(query_x)
        class_ids = sorted(prototypes.keys())
        proto_matrix = np.stack([prototypes[c] for c in class_ids], axis=0)
        dists = np.sum((embeddings[:, None, :] - proto_matrix[None, :, :]) ** 2, axis=2)
        closest = np.argmin(dists, axis=1)
        return np.array([class_ids[i] for i in closest], dtype=int)

    def train_episode(self, episode: Episode) -> Dict[str, float]:
        prototypes = self.compute_prototypes(episode.support_x, episode.support_y)
        preds = self.classify(episode.query_x, prototypes)
        acc = float(np.mean(preds == episode.query_y.astype(int)))
        self.prototypes = prototypes
        return {"accuracy": acc, "n_query": len(episode.query_y)}

    def evaluate_episode(self, episode: Episode) -> Dict[str, Any]:
        prototypes = self.compute_prototypes(episode.support_x, episode.support_y)
        preds = self.classify(episode.query_x, prototypes)
        acc = float(np.mean(preds == episode.query_y.astype(int)))
        return {"accuracy": acc, "predictions": preds}


class MatchingNetworks:
    def __init__(self, embedding_dim: int = 64):
        self.embedding_dim = embedding_dim
        self.support_set: Optional[Tuple[np.ndarray, np.ndarray]] = None

    def _encode(self, x: np.ndarray) -> np.ndarray:
        W = np.random.randn(x.shape[1], self.embedding_dim).astype(np.float64) * 0.1
        return x @ W

    def set_support(self, support_x: np.ndarray, support_y: np.ndarray) -> None:
        self.support_set = (support_x, support_y)

    def classify(self, query_x: np.ndarray) -> np.ndarray:
        if self.support_set is None:
            return np.zeros(len(query_x), dtype=int)
        support_x, support_y = self.support_set
        support_emb = self._encode(support_x)
        query_emb = self._encode(query_x)
        sims = query_emb @ support_emb.T
        weights = np.exp(sims - np.max(sims, axis=1, keepdims=True))
        weights = weights / np.sum(weights, axis=1, keepdims=True)
        classes = support_y.astype(int)
        unique_classes = np.unique(classes)
        scores = np.zeros((len(query_x), len(unique_classes)))
        for i, cls in enumerate(unique_classes):
            mask = classes == cls
            scores[:, i] = np.sum(weights[:, mask], axis=1)
        preds = unique_classes[np.argmax(scores, axis=1)]
        return preds
