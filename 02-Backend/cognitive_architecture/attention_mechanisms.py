import numpy as np
from typing import List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class AttentionMap:
    spatial_map: np.ndarray
    temporal_priority: np.ndarray
    semantic_relevance: float
    salience: float


class AttentionNetwork:
    def __init__(self, n_items: int = 64, hidden_dim: int = 32):
        self.n_items = n_items
        self.hidden_dim = hidden_dim
        self.w_q = np.random.randn(hidden_dim, n_items) * 0.01
        self.w_k = np.random.randn(hidden_dim, n_items) * 0.01
        self.w_v = np.random.randn(hidden_dim, n_items) * 0.01
        self._trained = False

    def forward(self, x: np.ndarray, mask: Optional[np.ndarray] = None) -> np.ndarray:
        if x.ndim == 1:
            if x.shape[0] != self.n_items:
                raise ValueError(f"Expected input size {self.n_items}, got {x.shape[0]}")
            q = self.w_q @ x
            k = self.w_k @ x
            v = self.w_v @ x
            score = float((q.T @ k) / np.sqrt(self.hidden_dim))
            if mask is not None:
                score = score if mask[0] else -1e9
            weight = np.exp(score - score)
            return weight * v
        if x.ndim == 2:
            q = x @ self.w_q.T
            k = x @ self.w_k.T
            v = x @ self.w_v.T
            scores = (q @ k.T) / np.sqrt(self.hidden_dim)
            if mask is not None:
                scores = np.where(mask, scores, -1e9)
            weights = self._softmax(scores, axis=-1)
            return weights @ v
        raise ValueError(f"Unsupported input ndim: {x.ndim}")

    def train_step(self, x: np.ndarray, target: np.ndarray, lr: float = 0.001) -> float:
        output = self.forward(x)
        error = target - output
        loss = float(np.mean(error ** 2))
        if x.ndim == 1:
            v_grad = -2 * error / len(error)
            self.w_v -= lr * np.outer(v_grad, x)
        else:
            v_grad = -2 * error / output.shape[0]
            self.w_v -= lr * (v_grad.T @ x)
        self._trained = True
        return loss

    def _softmax(self, x: np.ndarray, axis: int = -1) -> np.ndarray:
        e = np.exp(x - np.max(x, axis=axis, keepdims=True))
        return e / np.sum(e, axis=axis, keepdims=True)


class SpotlightModel:
    def __init__(self, fovea_radius: float = 0.2, peripheral_radius: float = 0.8, fovea_capacity: int = 4):
        self.fovea_radius = fovea_radius
        self.peripheral_radius = peripheral_radius
        self.fovea_capacity = fovea_capacity
        self._fovea_items: List[Any] = []
        self._peripheral_items: List[Any] = []

    def apply_spotlight(self, items: List[Any], positions: np.ndarray, focus_point: np.ndarray) -> Dict[str, List[Any]]:
        if len(items) == 0:
            return {"fovea": [], "peripheral": []}
        distances = np.linalg.norm(positions - focus_point, axis=1)
        fovea_mask = distances <= self.fovea_radius
        peripheral_mask = (distances > self.fovea_radius) & (distances <= self.peripheral_radius)
        fovea = [item for item, mask in zip(items, fovea_mask) if mask]
        peripheral = [item for item, mask in zip(items, peripheral_mask) if mask]
        if len(fovea) > self.fovea_capacity:
            fovea = fovea[: self.fovea_capacity]
        self._fovea_items = fovea
        self._peripheral_items = peripheral
        return {"fovea": fovea, "peripheral": peripheral}

    def shift_focus(self, new_focus: np.ndarray) -> np.ndarray:
        return new_focus

    def get_focus_quality(self) -> float:
        return len(self._fovea_items) / self.fovea_capacity if self.fovea_capacity > 0 else 0.0


class AttentionMechanisms:
    def __init__(self, n_items: int = 64, hidden_dim: int = 32):
        self.network = AttentionNetwork(n_items=n_items, hidden_dim=hidden_dim)
        self.spotlight = SpotlightModel()
        self._attention_history: List[Dict[str, Any]] = []

    def attend(self, items: List[Any], item_vectors: np.ndarray, focus_point: np.ndarray,
               positions: Optional[np.ndarray] = None) -> Dict[str, Any]:
        if item_vectors.ndim == 1:
            item_vectors = item_vectors.reshape(1, -1)
        batch_size = item_vectors.shape[0]
        effective_n_items = item_vectors.shape[1]
        if self.network.n_items != effective_n_items:
            saved_w_q = self.network.w_q
            saved_w_k = self.network.w_k
            saved_w_v = self.network.w_v
            self.network = AttentionNetwork(n_items=effective_n_items, hidden_dim=self.network.hidden_dim)
            self.network.w_q = saved_w_q[: self.network.hidden_dim, :effective_n_items]
            self.network.w_k = saved_w_k[: self.network.hidden_dim, :effective_n_items]
            self.network.w_v = saved_w_v[: self.network.hidden_dim, :effective_n_items]
        output = self.network.forward(item_vectors)
        if positions is None:
            positions = np.random.rand(len(items), 2)
        spotlight_result = self.spotlight.apply_spotlight(items, positions, focus_point)
        if output.ndim == 1:
            attention_scores = np.abs(output)
        else:
            attention_scores = np.mean(np.abs(output), axis=0)
        result = {
            "network_output": output.tolist() if output.ndim > 0 else [float(output)],
            "spotlight": spotlight_result,
            "attention_scores": attention_scores.tolist(),
        }
        self._attention_history.append(result)
        return result

    def train_attention(self, x: np.ndarray, target: np.ndarray, lr: float = 0.001) -> float:
        return self.network.train_step(x, target, lr=lr)

    def get_attention_stats(self) -> Dict[str, Any]:
        if not self._attention_history:
            return {"history_length": 0}
        return {
            "history_length": len(self._attention_history),
            "last_focus_quality": self.spotlight.get_focus_quality(),
        }
