import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field


@dataclass
class Episode:
    support_x: np.ndarray
    support_y: np.ndarray
    query_x: np.ndarray
    query_y: np.ndarray
    n_way: int = 5
    k_shot: int = 1


class AdvancedPrototypicalNetworks:
    def __init__(self, embedding_dim: int = 64, distance_metric: str = "euclidean"):
        self.embedding_dim = embedding_dim
        self.distance_metric = distance_metric
        self.prototypes: Dict[int, np.ndarray] = {}
        self.class_encoder: Dict[int, int] = {}
        self._next_code = 0
        self.log_vars: Dict[int, np.ndarray] = {}
        self.loss_history: List[float] = []

    def _encode(self, x: np.ndarray, stochastic: bool = False) -> np.ndarray:
        W = np.random.randn(x.shape[1], self.embedding_dim).astype(np.float64) * 0.1
        z = x @ W
        if stochastic and self.prototypes:
            log_var = np.mean([self.log_vars.get(c, np.zeros(self.embedding_dim, dtype=np.float64)) for c in self.prototypes], axis=0)
            noise = np.random.randn(*z.shape).astype(np.float64) * np.exp(0.5 * log_var)
            return z + noise
        return z

    def compute_prototypes(self, support_x: np.ndarray, support_y: np.ndarray) -> Dict[int, np.ndarray]:
        prototypes: Dict[int, np.ndarray] = {}
        log_vars: Dict[int, np.ndarray] = {}
        for cls in np.unique(support_y):
            mask = support_y == cls
            if int(cls) not in self.class_encoder:
                self.class_encoder[int(cls)] = self._next_code
                self._next_code += 1
            embeddings = self._encode(support_x[mask])
            proto = np.mean(embeddings, axis=0)
            lv = np.log(np.var(embeddings, axis=0) + 1e-6).astype(np.float64)
            prototypes[int(cls)] = proto
            log_vars[int(cls)] = lv
        self.prototypes = prototypes
        self.log_vars = log_vars
        return prototypes

    def _compute_distances(self, query_x: np.ndarray) -> np.ndarray:
        z = self._encode(query_x)
        if not self.prototypes:
            return np.zeros((len(query_x), 0))
        if self.distance_metric == "euclidean":
            z_q = z[:, None, :]
            z_p = np.stack([self.prototypes[c] for c in sorted(self.prototypes.keys())], axis=0)[None, :, :]
            return np.sum((z_q - z_p) ** 2, axis=2)
        else:
            z_norm = np.linalg.norm(z, axis=1, keepdims=True) + 1e-12
            p_norm = np.linalg.norm(np.stack([self.prototypes[c] for c in sorted(self.prototypes.keys())], axis=0), axis=1) + 1e-12
            cosine = (z @ np.stack([self.prototypes[c] for c in sorted(self.prototypes.keys())], axis=0).T) / (z_norm * p_norm[None, :])
            return 1.0 - cosine

    def classify(self, query_x: np.ndarray, prototypes: Optional[Dict[int, np.ndarray]] = None) -> np.ndarray:
        if prototypes is not None:
            self.prototypes = prototypes
        if not self.prototypes:
            return np.zeros(len(query_x), dtype=int)
        dists = self._compute_distances(query_x)
        closest = np.argmin(dists, axis=1)
        class_ids = sorted(self.prototypes.keys())
        return np.array([class_ids[i] for i in closest], dtype=int)

    def train_episode(self, episode: Episode, temperature: float = 1.0) -> Dict[str, float]:
        prototypes = self.compute_prototypes(episode.support_x, episode.support_y)
        z = self._encode(episode.query_x, stochastic=False)
        dists = self._compute_distances(episode.query_x)
        log_scores = -dists / temperature
        probs = np.exp(log_scores - np.max(log_scores, axis=1, keepdims=True))
        probs = probs / np.sum(probs, axis=1, keepdims=True)
        y_int = episode.query_y.astype(int)
        class_ids = sorted(prototypes.keys())
        target = np.zeros_like(probs)
        for i in range(len(y_int)):
            if y_int[i] in class_ids:
                target[i, class_ids.index(y_int[i])] = 1.0
            else:
                target[i, 0] = 1.0
        loss = float(-np.mean(np.sum(target * np.log(probs + 1e-12), axis=1)))
        self.loss_history.append(loss)
        preds = np.argmax(probs, axis=1)
        acc = float(np.mean(preds == np.array([class_ids[i] for i in np.argmax(target, axis=1)])))
        return {"loss": loss, "accuracy": acc, "n_query": len(episode.query_y)}

    def evaluate_episode(self, episode: Episode) -> Dict[str, Any]:
        z = self._encode(episode.query_x, stochastic=True)
        z_np = z
        z_np = episode.query_x @ np.random.randn(episode.query_x.shape[1], self.embedding_dim).astype(np.float64) * 0.1
        z = z_np
        dists = self._compute_distances(z)
        probs = np.exp(-dists / 1.0)
        probs = probs / np.sum(probs, axis=1, keepdims=True)
        preds = np.argmax(probs, axis=1)
        class_ids = sorted(self.prototypes.keys())
        preds = np.array([class_ids[i] for i in preds], dtype=int)
        acc = float(np.mean(preds == episode.query_y.astype(int)))
        return {"accuracy": acc, "predictions": preds, "probs": probs}


class RelationNetwork:
    def __init__(self, embedding_dim: int = 64, relation_dim: int = 64):
        self.embedding_dim = embedding_dim
        self.relation_dim = relation_dim
        self.eW = np.random.randn(2 * embedding_dim, relation_dim).astype(np.float64) * 0.1
        self.eb = np.zeros(relation_dim, dtype=np.float64)
        self.rW = np.random.randn(relation_dim, 1).astype(np.float64) * 0.1
        self.rb = np.zeros(1, dtype=np.float64)
        self.loss_history: List[float] = []

    @staticmethod
    def _relu(x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)

    def _embed(self, x: np.ndarray) -> np.ndarray:
        W = np.random.randn(x.shape[1], self.embedding_dim).astype(np.float64) * 0.1
        return x @ W

    def _relation_score(self, f_zi: np.ndarray, f_zj: np.ndarray) -> np.ndarray:
        concat = np.hstack([f_zi, f_zj])
        h = self._relu(concat @ self.eW + self.eb)
        return self._sigmoid(h @ self.rW + self.rb)

    @staticmethod
    def _sigmoid(x: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-x))

    def score_samples(self, support_x: np.ndarray, support_y: np.ndarray, query_x: np.ndarray) -> np.ndarray:
        f_s = self._embed(support_x)
        f_q = self._embed(query_x)
        scores = []
        for qi in range(len(query_x)):
            qi_scores = []
            for si in range(len(support_x)):
                s = self._relation_score(f_q[qi:qi+1], f_s[si:si+1])
                qi_scores.append(float(s))
            scores.append(qi_scores)
        return np.array(scores)

    def predict(self, support_x: np.ndarray, support_y: np.ndarray, query_x: np.ndarray) -> np.ndarray:
        scores = self.score_samples(support_x, support_y, query_x)
        preds = []
        for qi in range(len(query_x)):
            class_ids = np.unique(support_y)
            class_scores = {}
            for ci, c in enumerate(class_ids):
                mask = support_y == c
                class_scores[int(c)] = float(np.mean(scores[qi, mask])) if np.any(mask) else -1.0
            preds.append(max(class_scores, key=class_scores.get))
        return np.array(preds, dtype=int)

    def train_step(self, support_x: np.ndarray, support_y: np.ndarray, query_x: np.ndarray, query_y: np.ndarray,
                   lr: float = 0.01) -> float:
        scores = self.score_samples(support_x, support_y, query_x)
        scores_s = scores.reshape(-1, 1)
        support_y_rep = np.repeat(support_y.reshape(-1, 1), len(query_x), axis=0).reshape(-1)
        query_y_rep = np.tile(query_y.reshape(-1, 1), len(support_x)).reshape(-1)
        y_target = (support_y_rep == query_y_rep).astype(np.float64).reshape(-1, 1)
        f_s = self._embed(support_x)
        f_q = self._embed(query_x)
        concat = np.zeros((len(f_s) * len(f_q), 2 * self.embedding_dim), dtype=np.float64)
        idx = 0
        for qi in range(len(f_q)):
            for si in range(len(f_s)):
                concat[idx] = np.hstack([f_q[qi], f_s[si]])
                idx += 1
        h = self._relu(concat @ self.eW + self.eb)
        preds = self._sigmoid(h @ self.rW + self.rb)
        eps = 1e-12
        bce = -np.mean(y_target * np.log(preds + eps) + (1 - y_target) * np.log(1 - preds + eps))
        d_pred = preds - y_target
        d_rW = h.T @ d_pred / len(d_pred)
        d_rb = np.mean(d_pred, axis=0)
        dh = d_pred @ self.rW.T
        dh = dh * (h > 0)
        deW = concat.T @ dh / len(concat)
        deb = np.mean(dh, axis=0)
        self.rW -= lr * d_rW
        self.rb -= lr * d_rb
        self.eW -= lr * deW
        self.eb -= lr * deb
        self.loss_history.append(float(bce))
        return float(bce)

    def evaluate_step(self, support_x: np.ndarray, support_y: np.ndarray, query_x: np.ndarray,
                      query_y: np.ndarray) -> Dict[str, Any]:
        preds = self.predict(support_x, support_y, query_x)
        acc = float(np.mean(preds == query_y.astype(int)))
        return {"accuracy": acc, "predictions": preds}

    def get_few_shot_report(self) -> Dict[str, Any]:
        return {
            "steps": len(self.loss_history),
            "last_loss": float(self.loss_history[-1]) if self.loss_history else None,
            "min_loss": float(np.min(self.loss_history)) if self.loss_history else None,
        }
