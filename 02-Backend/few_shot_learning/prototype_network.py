import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import random


@dataclass
class Episode:
    support_x: np.ndarray
    support_y: np.ndarray
    query_x: np.ndarray
    query_y: np.ndarray
    n_way: int = 5
    k_shot: int = 1


class PrototypeNetwork:
    def __init__(
        self,
        embedding_dim: int = 64,
        distance_metric: str = "euclidean"
    ):
        self.embedding_dim = embedding_dim
        self.distance_metric = distance_metric
        self.prototypes: Dict[int, np.ndarray] = {}
        self.class_encoder: Dict[int, int] = {}
        self._next_code = 0
        self.loss_history: List[float] = []

    def _encode(self, x: np.ndarray) -> np.ndarray:
        rng = np.random.RandomState(42)
        W = rng.randn(x.shape[1], self.embedding_dim).astype(np.float64) * 0.1
        return x @ W

    def compute_prototypes(
        self,
        support_x: np.ndarray,
        support_y: np.ndarray
    ) -> Dict[int, np.ndarray]:
        prototypes: Dict[int, np.ndarray] = {}
        for cls in np.unique(support_y):
            mask = support_y == cls
            if int(cls) not in self.class_encoder:
                self.class_encoder[int(cls)] = self._next_code
                self._next_code += 1
            embeddings = self._encode(support_x[mask])
            prototypes[int(cls)] = np.mean(embeddings, axis=0)
        return prototypes

    def classify(
        self,
        query_x: np.ndarray,
        prototypes: Optional[Dict[int, np.ndarray]] = None
    ) -> np.ndarray:
        if prototypes is None:
            prototypes = self.prototypes
        if not prototypes:
            return np.zeros(len(query_x), dtype=int)
        embeddings = self._encode(query_x)
        class_ids = sorted(prototypes.keys())
        proto_matrix = np.stack([prototypes[c] for c in class_ids], axis=0)
        if self.distance_metric == "euclidean":
            dists = np.sum((embeddings[:, None, :] - proto_matrix[None, :, :]) ** 2, axis=2)
            closest = np.argmin(dists, axis=1)
        elif self.distance_metric == "cosine":
            emb_norm = np.linalg.norm(embeddings, axis=1, keepdims=True)
            proto_norm = np.linalg.norm(proto_matrix, axis=1, keepdims=True)
            normalized_emb = embeddings / np.clip(emb_norm, 1e-12, None)
            normalized_proto = proto_matrix / np.clip(proto_norm, 1e-12, None)
            sims = normalized_emb @ normalized_proto.T
            closest = np.argmax(sims, axis=1)
        else:
            raise ValueError(f"Unknown distance metric: {self.distance_metric}")
        return np.array([class_ids[i] for i in closest], dtype=int)

    def train_episode(self, episode: Episode) -> Dict[str, Any]:
        prototypes = self.compute_prototypes(episode.support_x, episode.support_y)
        preds = self.classify(episode.query_x, prototypes)
        acc = float(np.mean(preds == episode.query_y.astype(int)))
        self.prototypes = prototypes
        self.loss_history.append(1.0 - acc)
        return {"accuracy": acc, "n_query": len(episode.query_y)}

    def evaluate_episode(self, episode: Episode) -> Dict[str, Any]:
        prototypes = self.compute_prototypes(episode.support_x, episode.support_y)
        preds = self.classify(episode.query_x, prototypes)
        acc = float(np.mean(preds == episode.query_y.astype(int)))
        return {"accuracy": acc, "predictions": preds}

    def get_prototype_distances(
        self,
        x: np.ndarray
    ) -> Dict[int, np.ndarray]:
        if not self.prototypes:
            return {}
        embeddings = self._encode(x)
        class_ids = sorted(self.prototypes.keys())
        proto_matrix = np.stack([self.prototypes[c] for c in class_ids], axis=0)
        dists = np.sum((embeddings[:, None, :] - proto_matrix[None, :, :]) ** 2, axis=2)
        return {class_ids[i]: dists[:, i] for i in range(len(class_ids))}
