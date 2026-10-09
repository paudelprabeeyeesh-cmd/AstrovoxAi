import math
import random
from typing import Any, Dict, List, Optional

from .episode_sampler import Episode
from .similarity_classifier import _vec_dot


def _vec_norm(v: List[float]) -> float:
    return math.sqrt(sum(x * x for x in v))


def _mat_mul(a: List[List[float]], b: List[List[float]]) -> List[List[float]]:
    cols_a = len(a[0]) if a else 0
    cols_b = len(b[0]) if b else 0
    return [
        [sum(a[i][k] * b[k][j] for k in range(cols_a)) for j in range(cols_b)]
        for i in range(len(a))
    ]


class PrototypeNetwork:
    def __init__(
        self,
        embedding_dim: int = 64,
        distance_metric: str = "euclidean",
    ):
        self.embedding_dim = embedding_dim
        self.distance_metric = distance_metric
        self.prototypes: Dict[int, List[float]] = {}
        self.class_encoder: Dict[int, int] = {}
        self._next_code = 0
        self.loss_history: List[float] = []

    def _encode(self, x: List[List[float]]) -> List[List[float]]:
        input_dim = len(x[0]) if x else 0
        rng = random.Random(42)
        W = [
            [rng.gauss(0, 1) * 0.1 for _ in range(self.embedding_dim)]
            for _ in range(input_dim)
        ]
        return _mat_mul(x, W)

    def compute_prototypes(
        self,
        support_x: List[List[float]],
        support_y: List[int],
    ) -> Dict[int, List[float]]:
        prototypes: Dict[int, List[float]] = {}
        for cls in sorted(set(support_y)):
            mask = [i for i, label in enumerate(support_y) if label == cls]
            if int(cls) not in self.class_encoder:
                self.class_encoder[int(cls)] = self._next_code
                self._next_code += 1
            embeddings = self._encode([support_x[i] for i in mask])
            dim = len(embeddings[0]) if embeddings else 0
            proto = [
                sum(emb[c] for emb in embeddings) / len(embeddings)
                for c in range(dim)
            ]
            prototypes[int(cls)] = proto
        return prototypes

    def classify(
        self,
        query_x: List[List[float]],
        prototypes: Optional[Dict[int, List[float]]] = None,
    ) -> List[int]:
        if prototypes is None:
            prototypes = self.prototypes
        if not prototypes:
            return [0] * len(query_x)
        embeddings = self._encode(query_x)
        class_ids = sorted(prototypes.keys())
        proto_matrix = [prototypes[c] for c in class_ids]
        if self.distance_metric == "euclidean":
            preds = []
            for e in embeddings:
                dists = [
                    sum((ei - pi) ** 2 for ei, pi in zip(e, p))
                    for p in proto_matrix
                ]
                best = min(range(len(dists)), key=dists.__getitem__)
                preds.append(class_ids[best])
            return preds
        elif self.distance_metric == "cosine":
            preds = []
            for e in embeddings:
                e_norm = _vec_norm(e)
                if e_norm == 0:
                    e_norm = 1e-12
                e_unit = [v / e_norm for v in e]
                sims = [_vec_dot(e_unit, p) for p in proto_matrix]
                best = max(range(len(sims)), key=sims.__getitem__)
                preds.append(class_ids[best])
            return preds
        else:
            raise ValueError(f"Unknown distance metric: {self.distance_metric}")

    def train_episode(self, episode: Episode) -> Dict[str, Any]:
        prototypes = self.compute_prototypes(episode.support_x, episode.support_y)
        preds = self.classify(episode.query_x, prototypes)
        acc = (
            sum(1 for p, y in zip(preds, episode.query_y) if p == y)
            / len(episode.query_y)
        )
        self.prototypes = prototypes
        self.loss_history.append(1.0 - acc)
        return {"accuracy": acc, "n_query": len(episode.query_y)}

    def evaluate_episode(self, episode: Episode) -> Dict[str, Any]:
        prototypes = self.compute_prototypes(episode.support_x, episode.support_y)
        preds = self.classify(episode.query_x, prototypes)
        acc = (
            sum(1 for p, y in zip(preds, episode.query_y) if p == y)
            / len(episode.query_y)
        )
        return {"accuracy": acc, "predictions": preds}

    def get_prototype_distances(
        self, x: List[List[float]]
    ) -> Dict[int, List[float]]:
        if not self.prototypes:
            return {}
        embeddings = self._encode(x)
        class_ids = sorted(self.prototypes.keys())
        proto_matrix = [self.prototypes[c] for c in class_ids]
        dists = {}
        for c_idx, c in enumerate(class_ids):
            proto = proto_matrix[c_idx]
            class_dists = [
                sum((ei - pi) ** 2 for ei, pi in zip(e, proto)) for e in embeddings
            ]
            dists[c] = class_dists
        return dists
