import numpy as np
from typing import Dict, List, Optional, Tuple, Any


class AdvancedTransferLearning:
    def __init__(self, input_dim: int, hidden_dim: int = 64, output_dim: int = 5,
                 lr: float = 0.01, frozen_layers: List[str] = None):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.lr = lr
        self.frozen_layers = frozen_layers or []
        self.params: Dict[str, np.ndarray] = {}
        self.loss_history: List[float] = []
        self.source_accuracy: Optional[float] = None
        self.target_accuracy: Optional[float] = None
        self.domain_weights: Optional[np.ndarray] = None
        self._initialize_params()

    def _initialize_params(self) -> None:
        self.params["W1"] = np.random.randn(self.input_dim, self.hidden_dim).astype(np.float64) * 0.1
        self.params["b1"] = np.zeros(self.hidden_dim, dtype=np.float64)
        self.params["W2"] = np.random.randn(self.hidden_dim, self.hidden_dim).astype(np.float64) * 0.1
        self.params["b2"] = np.zeros(self.hidden_dim, dtype=np.float64)
        self.params["W3"] = np.random.randn(self.hidden_dim, self.output_dim).astype(np.float64) * 0.1
        self.params["b3"] = np.zeros(self.output_dim, dtype=np.float64)

    @staticmethod
    def _relu(x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)

    @staticmethod
    def _softmax(x: np.ndarray) -> np.ndarray:
        e = np.exp(x - np.max(x, axis=1, keepdims=True))
        return e / np.sum(e, axis=1, keepdims=True)

    def _forward(self, x: np.ndarray, params: Optional[Dict[str, np.ndarray]] = None) -> Tuple[np.ndarray, np.ndarray]:
        p = params if params is not None else self.params
        h1 = self._relu(x @ p["W1"] + p["b1"])
        h2 = self._relu(h1 @ p["W2"] + p["b2"])
        logits = h2 @ p["W3"] + p["b3"]
        return h2, logits

    def _compute_loss(self, logits: np.ndarray, y: np.ndarray) -> float:
        probs = self._softmax(logits)
        y_int = y.astype(int)
        return float(-np.mean(np.log(probs[np.arange(len(y_int)), y_int] + 1e-12)))

    def freeze_layer(self, layer_name: str) -> None:
        if layer_name not in self.frozen_layers:
            self.frozen_layers.append(layer_name)

    def unfreeze_layer(self, layer_name: str) -> None:
        if layer_name in self.frozen_layers:
            self.frozen_layers.remove(layer_name)

    def load_source_weights(self, source_params: Dict[str, np.ndarray]) -> None:
        for k in source_params:
            if k in self.params:
                self.params[k] = source_params[k].astype(np.float64)

    def fine_tune_step(self, x: np.ndarray, y: np.ndarray, lr: Optional[float] = None) -> float:
        lr = lr if lr is not None else self.lr
        h, logits = self._forward(x)
        loss = self._compute_loss(logits, y)
        self.loss_history.append(loss)
        probs = self._softmax(logits)
        y_int = y.astype(int)
        grad = probs.copy()
        grad[np.arange(len(y_int)), y_int] -= 1
        grad /= len(y_int)
        dW3 = h.T @ grad
        db3 = np.sum(grad, axis=0)
        dh = grad @ self.params["W3"].T
        dh = dh * (h > 0)
        dW2 = h.T @ dh
        db2 = np.sum(dh, axis=0)
        dh2 = dh
        dW1 = x.T @ ((dh2 @ self.params["W2"].T) * (self._relu(x @ self.params["W1"] + self.params["b1"]) > 0))
        db1 = np.sum(((dh2 @ self.params["W2"].T) * (self._relu(x @ self.params["W1"] + self.params["b1"]) > 0)), axis=0)
        if "W1" not in self.frozen_layers:
            self.params["W1"] -= lr * dW1
            self.params["b1"] -= lr * db1
        if "W2" not in self.frozen_layers:
            self.params["W2"] -= lr * dW2
            self.params["b2"] -= lr * db2
        if "W3" not in self.frozen_layers:
            self.params["W3"] -= lr * dW3
            self.params["b3"] -= lr * db3
        return loss

    def domain_adaptation_step(self, source_x: np.ndarray, source_y: np.ndarray,
                                target_x: np.ndarray, lr: Optional[float] = None) -> float:
        lr = lr if lr is not None else self.lr
        _, logits_s = self._forward(source_x)
        loss_cls = self._compute_loss(logits_s, source_y)
        _, feats_s = self._forward(source_x)
        _, feats_t = self._forward(target_x)
        mmd_loss = self._mmd_loss(feats_s, feats_t)
        loss = loss_cls + 0.1 * mmd_loss
        self.loss_history.append(loss)
        all_x = np.vstack([source_x, target_x])
        _, all_logits = self._forward(all_x)
        probs = self._softmax(all_logits)
        y_int = np.concatenate([source_y.astype(int), np.zeros(len(target_x), dtype=int)])
        grad = probs.copy()
        grad[np.arange(len(y_int)), y_int] -= 1
        grad[:len(source_x)] /= len(source_x)
        grad[len(source_x):] /= len(target_x)
        h_all = self._relu(all_x @ self.params["W1"] + self.params["b1"])
        dW3 = h_all.T @ grad
        db3 = np.sum(grad, axis=0)
        dh = grad @ self.params["W3"].T
        dh = dh * (h_all > 0)
        dW2 = h_all.T @ dh
        db2 = np.sum(dh, axis=0)
        dW1 = all_x.T @ ((dh @ self.params["W2"].T) * (self._relu(all_x @ self.params["W1"] + self.params["b1"]) > 0))
        db1 = np.sum(((dh @ self.params["W2"].T) * (self._relu(all_x @ self.params["W1"] + self.params["b1"]) > 0)), axis=0)
        if "W1" not in self.frozen_layers:
            self.params["W1"] -= lr * dW1
            self.params["b1"] -= lr * db1
        if "W2" not in self.frozen_layers:
            self.params["W2"] -= lr * dW2
            self.params["b2"] -= lr * db2
        if "W3" not in self.frozen_layers:
            self.params["W3"] -= lr * dW3
            self.params["b3"] -= lr * db3
        return loss

    def _mmd_loss(self, feats_s: np.ndarray, feats_t: np.ndarray, gamma: float = 1.0) -> float:
        def rbf_kernel(x1, x2):
            dist = np.sum((x1[:, None, :] - x2[None, :, :]) ** 2, axis=2)
            return np.exp(-gamma * dist)
        k_ss = rbf_kernel(feats_s, feats_s)
        k_tt = rbf_kernel(feats_t, feats_t)
        k_st = rbf_kernel(feats_s, feats_t)
        return float(np.mean(k_ss) + np.mean(k_tt) - 2 * np.mean(k_st))

    def transfer_task(self, support_x: np.ndarray, support_y: np.ndarray, query_x: np.ndarray,
                      steps: int = 5, lr: Optional[float] = None) -> np.ndarray:
        lr = lr if lr is not None else self.lr * 10
        for _ in range(steps):
            idx = np.random.choice(len(support_x), size=min(8, len(support_x)), replace=False)
            xb = support_x[idx]
            yb = support_y[idx]
            self.fine_tune_step(xb, yb, lr=lr)
        _, logits = self._forward(query_x)
        probs = self._softmax(logits)
        return np.argmax(probs, axis=1)

    def get_transfer_report(self) -> Dict[str, Any]:
        return {
            "frozen_layers": self.frozen_layers,
            "total_steps": len(self.loss_history),
            "last_loss": float(self.loss_history[-1]) if self.loss_history else None,
            "source_accuracy": self.source_accuracy,
            "target_accuracy": self.target_accuracy,
            "transfer_accuracy": self.target_accuracy,
        }
