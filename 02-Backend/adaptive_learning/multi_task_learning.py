import numpy as np
from typing import Dict, List, Optional, Tuple


class MultiTaskModel:
    def __init__(self, shared_dim: int = 64, task_dims: Optional[Dict[str, int]] = None):
        self.shared_dim = shared_dim
        self.task_dims = task_dims or {}
        self.shared_params: Dict[str, np.ndarray] = {}
        self.task_params: Dict[str, Dict[str, np.ndarray]] = {}
        self.loss_history: Dict[str, List[float]] = {}
        self.task_weights: Dict[str, float] = {}

    def add_task(self, task_name: str, output_dim: int) -> None:
        self.task_dims[task_name] = output_dim
        self.task_params[task_name] = {
            "W": np.random.randn(self.shared_dim, output_dim).astype(np.float64) * 0.1,
            "b": np.zeros(output_dim, dtype=np.float64),
        }
        self.loss_history[task_name] = []
        self.task_weights[task_name] = 1.0

    def set_task_weights(self, weights: Dict[str, float]) -> None:
        for name, w in weights.items():
            if name in self.task_weights:
                self.task_weights[name] = float(w)

    def init_shared(self, input_dim: int) -> None:
        self.shared_params = {
            "W": np.random.randn(input_dim, self.shared_dim).astype(np.float64) * 0.1,
            "b": np.zeros(self.shared_dim, dtype=np.float64),
        }

    def forward(self, x: np.ndarray, task_name: str) -> np.ndarray:
        h = x @ self.shared_params["W"] + self.shared_params["b"]
        h = np.maximum(0, h)
        W = self.task_params[task_name]["W"]
        b = self.task_params[task_name]["b"]
        return h @ W + b

    def train_step(self, x: np.ndarray, y: np.ndarray, task_name: str, lr: float = 0.001) -> float:
        logits = self.forward(x, task_name)
        loss, grad = self._compute_loss_and_grad(logits, y)
        self._backward(x, grad, task_name, lr)
        self.loss_history[task_name].append(float(loss))
        return float(loss)

    def _compute_loss_and_grad(self, logits: np.ndarray, y: np.ndarray) -> Tuple[float, np.ndarray]:
        probs = self._softmax(logits)
        loss = -np.mean(np.log(probs[np.arange(len(y)), y.astype(int)] + 1e-12))
        grad = (probs - np.eye(probs.shape[1])[y.astype(int)]) / len(y)
        return loss, grad

    @staticmethod
    def _softmax(x: np.ndarray) -> np.ndarray:
        e = np.exp(x - np.max(x, axis=1, keepdims=True))
        return e / np.sum(e, axis=1, keepdims=True)

    def _backward(self, x: np.ndarray, grad_logits: np.ndarray, task_name: str, lr: float) -> None:
        h = np.maximum(0, x @ self.shared_params["W"] + self.shared_params["b"])
        grad_task_W = (h.T @ grad_logits) / len(h)
        self.task_params[task_name]["W"] -= lr * grad_task_W
        W = self.task_params[task_name]["W"]
        grad_shared = (grad_logits @ W.T) * (h > 0)
        self.shared_params["W"] -= lr * (x.T @ grad_shared) / len(x)
        self.shared_params["b"] -= lr * np.mean(grad_shared, axis=0)

    def multi_task_train_step(self, batches: Dict[str, Tuple[np.ndarray, np.ndarray]], lr: float = 0.001) -> Dict[str, float]:
        total_loss = 0.0
        losses = {}
        for task_name, (x, y) in batches.items():
            loss = self.train_step(x, y, task_name, lr)
            losses[task_name] = loss
            total_loss += self.task_weights.get(task_name, 1.0) * loss
        return {"total_loss": float(total_loss), "task_losses": losses}

    def get_task_weights(self) -> Dict[str, float]:
        return dict(self.task_weights)
