import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field


class WeaklySupervisedLearner:
    def __init__(self, input_dim: int, hidden_dim: int = 64, num_classes: int = 2,
                 lr: float = 0.01, pooling: str = "attention"):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_classes = num_classes
        self.lr = lr
        self.pooling = pooling
        self.params: Dict[str, np.ndarray] = {}
        self.attention_params: Dict[str, np.ndarray] = {}
        self.loss_history: List[float] = []
        self.bag_accuracy: List[float] = []
        self._initialize_params()

    def _initialize_params(self) -> None:
        self.params["W1"] = np.random.randn(self.input_dim, self.hidden_dim).astype(np.float64) * 0.1
        self.params["b1"] = np.zeros(self.hidden_dim, dtype=np.float64)
        self.params["W2"] = np.random.randn(self.hidden_dim, self.num_classes).astype(np.float64) * 0.1
        self.params["b2"] = np.zeros(self.num_classes, dtype=np.float64)
        if self.pooling == "attention":
            self.attention_params["V"] = np.random.randn(self.hidden_dim, 1).astype(np.float64) * 0.1
            self.attention_params["b"] = np.zeros(1, dtype=np.float64)

    @staticmethod
    def _relu(x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)

    @staticmethod
    def _softmax(x: np.ndarray) -> np.ndarray:
        if x.ndim == 1:
            x = x.reshape(1, -1)
        e = np.exp(x - np.max(x, axis=1, keepdims=True))
        return e / np.sum(e, axis=1, keepdims=True)

    def _instance_forward(self, x: np.ndarray) -> np.ndarray:
        h = self._relu(x @ self.params["W1"] + self.params["b1"])
        return h @ self.params["W2"] + self.params["b2"]

    def _pool(self, h: np.ndarray) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        if self.pooling == "max":
            return np.max(h, axis=0), None
        elif self.pooling == "mean":
            return np.mean(h, axis=0), None
        else:
            scores = h @ self.attention_params["V"] + self.attention_params["b"]
            alpha = self._softmax(scores.flatten())
            alpha = alpha.reshape(-1)
            bag_vec = np.sum(alpha[:, None] * h, axis=0)
            return bag_vec, alpha

    def forward_bag(self, x: np.ndarray) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        h = self._relu(x @ self.params["W1"] + self.params["b1"])
        bag_vec, alpha = self._pool(h)
        logits = bag_vec @ self.params["W2"] + self.params["b2"]
        return logits, alpha

    def _compute_loss(self, logits: np.ndarray, y: int) -> float:
        probs = self._softmax(logits.reshape(1, -1))
        return float(-np.log(probs[0, int(y)] + 1e-12))

    def train_bag(self, x: np.ndarray, y: int, lr: Optional[float] = None) -> float:
        lr = lr if lr is not None else self.lr
        logits, alpha = self.forward_bag(x)
        loss = self._compute_loss(logits, y)
        self.loss_history.append(loss)
        h = self._relu(x @ self.params["W1"] + self.params["b1"])
        if self.pooling == "attention" and alpha is not None:
            att = np.sum(alpha.reshape(-1, 1) * h, axis=0)
            logits = att @ self.params["W2"] + self.params["b2"]
        else:
            logits = logits.reshape(1, -1)
        probs = self._softmax(logits)
        y_idx = np.array([int(y)])
        grad = probs.copy()
        grad[0, y_idx] -= 1
        dW2 = h.T @ grad
        db2 = np.sum(grad, axis=0)
        if self.pooling == "attention" and alpha is not None:
            dalpha = h @ self.params["W2"].T @ grad.T
            dalpha = dalpha.flatten()
            dv = (h.T @ dalpha[:, None]).flatten()
            dV = dv.reshape(-1, 1)
            db = np.sum(dalpha)
            self.attention_params["V"] -= lr * dV
            self.attention_params["b"] -= lr * db
        dh = grad @ self.params["W2"].T
        dh = dh * (h > 0)
        dW1 = x.T @ dh
        db1 = np.sum(dh, axis=0)
        self.params["W1"] -= lr * dW1
        self.params["b1"] -= lr * db1
        self.params["W2"] -= lr * dW2
        self.params["b2"] -= lr * db2
        return loss

    def predict_bag(self, x: np.ndarray) -> int:
        logits, _ = self.forward_bag(x)
        probs = self._softmax(logits.reshape(1, -1))
        return int(np.argmax(probs, axis=1)[0])

    def instance_classify(self, x: np.ndarray) -> np.ndarray:
        logits = self._instance_forward(x)
        probs = self._softmax(logits)
        return np.argmax(probs, axis=1)

    def get_mil_report(self) -> Dict[str, Any]:
        return {
            "total_steps": len(self.loss_history),
            "last_loss": float(self.loss_history[-1]) if self.loss_history else None,
            "pooling": self.pooling,
            "bag_accuracy": float(np.mean(self.bag_accuracy[-10:])) if self.bag_accuracy else None,
        }
