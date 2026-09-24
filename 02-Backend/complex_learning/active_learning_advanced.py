import numpy as np
from typing import Dict, List, Optional, Tuple, Any


class ActiveLearner:
    def __init__(self, input_dim: int, hidden_dim: int = 64, output_dim: int = 5,
                 batch_size: int = 10):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.batch_size = batch_size
        self.params: Dict[str, np.ndarray] = {}
        self.loss_history: List[float] = []
        self.labeled_indices: List[int] = []
        self.unlabeled_indices: List[int] = []
        self._initialize_params()

    def _initialize_params(self) -> None:
        self.params["W1"] = np.random.randn(self.input_dim, self.hidden_dim).astype(np.float64) * 0.1
        self.params["b1"] = np.zeros(self.hidden_dim, dtype=np.float64)
        self.params["W2"] = np.random.randn(self.hidden_dim, self.output_dim).astype(np.float64) * 0.1
        self.params["b2"] = np.zeros(self.output_dim, dtype=np.float64)

    @staticmethod
    def _relu(x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)

    @staticmethod
    def _softmax(x: np.ndarray) -> np.ndarray:
        e = np.exp(x - np.max(x, axis=1, keepdims=True))
        return e / np.sum(e, axis=1, keepdims=True)

    def _forward(self, x: np.ndarray) -> np.ndarray:
        h = self._relu(x @ self.params["W1"] + self.params["b1"])
        return h @ self.params["W2"] + self.params["b2"]

    def _compute_loss(self, logits: np.ndarray, y: np.ndarray) -> float:
        probs = self._softmax(logits)
        y_int = y.astype(int)
        return float(-np.mean(np.log(probs[np.arange(len(y_int)), y_int] + 1e-12)))

    def fit(self, x: np.ndarray, y: np.ndarray) -> None:
        lr = 0.01
        for _ in range(5):
            logits = self._forward(x)
            loss = self._compute_loss(logits, y)
            self.loss_history.append(loss)
            probs = self._softmax(logits)
            y_int = y.astype(int)
            grad = probs.copy()
            grad[np.arange(len(y_int)), y_int] -= 1
            grad /= len(y_int)
            h = np.maximum(x @ self.params["W1"] + self.params["b1"], 0)
            dW2 = h.T @ grad
            db2 = np.sum(grad, axis=0)
            dh = grad @ self.params["W2"].T
            dh = dh * (h > 0)
            dW1 = x.T @ dh
            db1 = np.sum(dh, axis=0)
            self.params["W1"] -= lr * dW1
            self.params["b1"] -= lr * db1
            self.params["W2"] -= lr * dW2
            self.params["b2"] -= lr * db2

    def set_dataset(self, x: np.ndarray, labeled_idx: List[int]) -> None:
        self.labeled_indices = list(labeled_idx)
        self.unlabeled_indices = [i for i in range(len(x)) if i not in self.labeled_indices]
        self._x = x

    def entropy_sampling(self, x_unlabeled: np.ndarray) -> np.ndarray:
        logits = self._forward(x_unlabeled)
        probs = self._softmax(logits)
        entropy = -np.sum(probs * np.log(probs + 1e-12), axis=1)
        return entropy

    def margin_sampling(self, x_unlabeled: np.ndarray) -> np.ndarray:
        logits = self._forward(x_unlabeled)
        probs = self._softmax(logits)
        sorted_probs = np.sort(probs, axis=1)
        margins = sorted_probs[:, -1] - sorted_probs[:, -2]
        return -margins

    def uncertainty_sampling(self, x_unlabeled: np.ndarray,
                             method: str = "entropy") -> np.ndarray:
        if method == "entropy":
            return self.entropy_sampling(x_unlabeled)
        elif method == "margin":
            return self.margin_sampling(x_unlabeled)
        else:
            scores = self.entropy_sampling(x_unlabeled) + self.margin_sampling(x_unlabeled)
            return scores

    def expected_model_change(self, x_unlabeled: np.ndarray) -> np.ndarray:
        logits = self._forward(x_unlabeled)
        probs = self._softmax(logits)
        scores = np.sum(probs ** 2, axis=1)
        return scores

    def query_by_committee(self, x_unlabeled: np.ndarray,
                           num_committee: int = 3) -> np.ndarray:
        committee_preds = []
        for _ in range(num_committee):
            noise = np.random.randn(self.hidden_dim, self.output_dim).astype(np.float64) * 0.01
            params = {k: v.copy() for k, v in self.params.items()}
            params["W2"] = params["W2"] + noise
            logits = x_unlabeled @ np.random.randn(x_unlabeled.shape[1], self.hidden_dim).astype(np.float64) * 0.01
            logits = np.maximum(logits, 0) @ params["W2"] + params["b2"]
            probs = self._softmax(logits)
            committee_preds.append(probs)
        consensus = np.mean(committee_preds, axis=0)
        entropy = -np.sum(consensus * np.log(consensus + 1e-12), axis=1)
        return entropy

    def core_set_selection(self, x_labeled: np.ndarray, x_unlabeled: np.ndarray,
                           k: int = 10) -> np.ndarray:
        labeled_feats = np.maximum(x_labeled @ self.params["W1"] + self.params["b1"], 0)
        unlabeled_feats = np.maximum(x_unlabeled @ self.params["W1"] + self.params["b1"], 0)
        selected = []
        remaining = list(range(len(unlabeled_feats)))
        for _ in range(min(k, len(unlabeled_feats))):
            if not remaining:
                break
            if not selected:
                dists = np.min(np.sum((labeled_feats[:, None, :] - unlabeled_feats[None, remaining, :]) ** 2, axis=2), axis=0)
                idx = np.argmax(dists)
                selected.append(remaining[idx])
                remaining.pop(idx)
            else:
                sel_feats = unlabeled_feats[selected]
                min_dists = np.min(np.sum((sel_feats[:, None, :] - unlabeled_feats[None, remaining, :]) ** 2, axis=2), axis=0)
                idx = np.argmax(min_dists)
                selected.append(remaining[idx])
                remaining.pop(idx)
        return np.array(selected, dtype=int)

    def vaal_selection(self, x_labeled: np.ndarray, x_unlabeled: np.ndarray,
                       k: int = 10) -> np.ndarray:
        labeled_feats = np.maximum(x_labeled @ self.params["W1"] + self.params["b1"], 0)
        unlabeled_feats = np.maximum(x_unlabeled @ self.params["W1"] + self.params["b1"], 0)
        scores = np.zeros(len(unlabeled_feats))
        for i in range(len(unlabeled_feats)):
            min_dist = np.min(np.sum((labeled_feats - unlabeled_feats[i]) ** 2, axis=1))
            scores[i] = min_dist
        if k >= len(scores):
            return np.arange(len(scores))
        return np.argsort(scores)[-k:]

    def select_samples(self, x_unlabeled: np.ndarray, method: str = "entropy",
                       x_labeled: Optional[np.ndarray] = None,
                       k: Optional[int] = None) -> np.ndarray:
        k = k if k is not None else self.batch_size
        if method in ["entropy", "margin", "uncertainty"]:
            scores = self.uncertainty_sampling(x_unlabeled, method=method)
        elif method == "model_change":
            scores = self.expected_model_change(x_unlabeled)
        elif method == "core_set":
            if x_labeled is None:
                scores = self.entropy_sampling(x_unlabeled)
            else:
                selected = self.core_set_selection(x_labeled, x_unlabeled, k=k)
                return selected
            return np.array([], dtype=int)
        elif method == "vaal":
            if x_labeled is None:
                scores = self.entropy_sampling(x_unlabeled)
            else:
                selected = self.vaal_selection(x_labeled, x_unlabeled, k=k)
                return selected
            return np.array([], dtype=int)
        elif method == "committee":
            scores = self.query_by_committee(x_unlabeled)
        else:
            scores = self.entropy_sampling(x_unlabeled)
        if k >= len(scores):
            return np.arange(len(scores))
        return np.argsort(scores)[-k:]

    def get_active_report(self) -> Dict[str, Any]:
        return {
            "num_labeled": len(self.labeled_indices),
            "num_unlabeled": len(self.unlabeled_indices),
            "num_steps": len(self.loss_history),
            "last_loss": float(self.loss_history[-1]) if self.loss_history else None,
        }
