import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field


@dataclass
class FewShotConfig:
    input_dim: int
    num_classes: int
    num_support: int = 5
    num_query: int = 15
    embedding_dim: int = 64
    distance_metric: str = "euclidean"


class PrototypicalNetwork:
    def __init__(self, config: FewShotConfig):
        self.config = config
        self.embedding_params: Dict[str, np.ndarray] = {}
        self.loss_history: List[float] = []
        self._initialize_params()

    def _initialize_params(self) -> None:
        d = self.config.input_dim
        e = self.config.embedding_dim
        self.embedding_params['W1'] = np.random.randn(d, e).astype(np.float64) * np.sqrt(2.0 / d)
        self.embedding_params['b1'] = np.zeros(e, dtype=np.float64)
        self.embedding_params['W2'] = np.random.randn(e, e).astype(np.float64) * np.sqrt(2.0 / e)
        self.embedding_params['b2'] = np.zeros(e, dtype=np.float64)

    @staticmethod
    def _relu(x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)

    def _embed(self, x: np.ndarray) -> np.ndarray:
        h = self._relu(x @ self.embedding_params['W1'] + self.embedding_params['b1'])
        return h @ self.embedding_params['W2'] + self.embedding_params['b2']

    def _compute_prototypes(self, support_embeddings: np.ndarray, support_labels: np.ndarray) -> np.ndarray:
        num_classes = self.config.num_classes
        prototypes = []
        for c in range(num_classes):
            mask = support_labels == c
            if np.sum(mask) > 0:
                prototypes.append(np.mean(support_embeddings[mask], axis=0))
            else:
                prototypes.append(np.zeros(self.config.embedding_dim, dtype=np.float64))
        return np.array(prototypes)

    def _compute_distances(self, query_embeddings: np.ndarray, prototypes: np.ndarray) -> np.ndarray:
        if self.config.distance_metric == "euclidean":
            return np.sum((query_embeddings[:, None, :] - prototypes[None, :, :]) ** 2, axis=2)
        elif self.config.distance_metric == "cosine":
            q = query_embeddings / (np.linalg.norm(query_embeddings, axis=1, keepdims=True) + 1e-12)
            p = prototypes / (np.linalg.norm(prototypes, axis=1, keepdims=True) + 1e-12)
            return 1 - (q @ p.T)
        else:
            return np.sum((query_embeddings[:, None, :] - prototypes[None, :, :]) ** 2, axis=2)

    def _compute_loss(self, distances: np.ndarray, query_labels: np.ndarray) -> float:
        num_classes = self.config.num_classes
        target = np.zeros_like(distances)
        target[np.arange(len(query_labels)), query_labels] = 1.0
        logits = -distances
        logits = logits - np.max(logits, axis=1, keepdims=True)
        exp_logits = np.exp(logits)
        probs = exp_logits / np.sum(exp_logits, axis=1, keepdims=True)
        loss = float(-np.mean(np.log(probs[np.arange(len(query_labels)), query_labels] + 1e-12)))
        return loss

    def train_episode(self, support_x: np.ndarray, support_y: np.ndarray, query_x: np.ndarray, query_y: np.ndarray, lr: float = 0.01) -> Dict[str, Any]:
        support_emb = self._embed(support_x)
        query_emb = self._embed(query_x)
        prototypes = self._compute_prototypes(support_emb, support_y)
        distances = self._compute_distances(query_emb, prototypes)
        loss = self._compute_loss(distances, query_y)
        self.loss_history.append(loss)
        num_classes = self.config.num_classes
        target = np.zeros_like(distances)
        target[np.arange(len(query_y)), query_y] = 1.0
        logits = -distances
        logits = logits - np.max(logits, axis=1, keepdims=True)
        exp_logits = np.exp(logits)
        probs = exp_logits / np.sum(exp_logits, axis=1, keepdims=True)
        grad = probs - target
        grad /= len(query_y)
        d_emb = grad[:, None, :] @ prototypes[None, :, :]
        d_emb = np.sum(d_emb, axis=1)
        h = self._relu(support_x @ self.embedding_params['W1'] + self.embedding_params['b1'])
        h_q = self._relu(query_x @ self.embedding_params['W1'] + self.embedding_params['b1'])
        db2_q = np.sum(d_emb, axis=0)
        dw2_q = h_q.T @ d_emb
        dh_q = d_emb @ self.embedding_params['W2'].T * (h_q > 0).astype(np.float64)
        db1_q = np.sum(dh_q, axis=0)
        dw1_q = query_x.T @ dh_q
        self.embedding_params['W2'] -= lr * dw2_q
        self.embedding_params['b2'] -= lr * db2_q
        self.embedding_params['W1'] -= lr * dw1_q
        self.embedding_params['b1'] -= lr * db1_q
        return {'loss': loss, 'accuracy': float(np.mean(np.argmin(distances, axis=1) == query_y))}

    def predict(self, support_x: np.ndarray, support_y: np.ndarray, query_x: np.ndarray) -> np.ndarray:
        support_emb = self._embed(support_x)
        query_emb = self._embed(query_x)
        prototypes = self._compute_prototypes(support_emb, support_y)
        distances = self._compute_distances(query_emb, prototypes)
        return np.argmin(distances, axis=1)

    def get_few_shot_report(self) -> Dict[str, Any]:
        return {
            'num_episodes': len(self.loss_history),
            'last_loss': float(self.loss_history[-1]) if self.loss_history else None,
            'mean_loss': float(np.mean(self.loss_history[-10:])) if len(self.loss_history) >= 10 else (float(self.loss_history[-1]) if self.loss_history else None),
            'num_classes': self.config.num_classes,
            'embedding_dim': self.config.embedding_dim,
            'distance_metric': self.config.distance_metric,
        }
