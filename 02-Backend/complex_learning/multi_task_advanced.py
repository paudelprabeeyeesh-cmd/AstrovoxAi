import numpy as np
from typing import Dict, List, Optional, Tuple, Any


class AdvancedMultiTaskModel:
    def __init__(self, shared_dim: int = 64, task_hidden_dim: int = 64,
                 lr: float = 0.01, uncertainty_weighting: bool = True,
                 pc_grad: bool = False):
        self.shared_dim = shared_dim
        self.task_hidden_dim = task_hidden_dim
        self.lr = lr
        self.uncertainty_weighting = uncertainty_weighting
        self.pc_grad = pc_grad
        self.shared_params: Dict[str, np.ndarray] = {}
        self.task_params: Dict[str, Dict[str, np.ndarray]] = {}
        self.task_weights: Dict[str, float] = {}
        self.log_vars: Dict[str, np.ndarray] = {}
        self.loss_history: List[float] = []
        self.task_losses: Dict[str, List[float]] = {}
        self._next_task_id: int = 0

    def init_shared(self, input_dim: int) -> None:
        self.shared_params["W1"] = np.random.randn(input_dim, self.shared_dim).astype(np.float64) * 0.1
        self.shared_params["b1"] = np.zeros(self.shared_dim, dtype=np.float64)

    def add_task(self, task_name: str, output_dim: int) -> None:
        if task_name in self.task_params:
            return
        self.task_params[task_name] = {
            "W": np.random.randn(self.shared_dim, output_dim).astype(np.float64) * 0.1,
            "b": np.zeros(output_dim, dtype=np.float64),
        }
        self.task_weights[task_name] = 1.0
        self.log_vars[task_name] = np.zeros(1, dtype=np.float64)
        self._next_task_id += 1

    def set_task_weights(self, weights: Dict[str, float]) -> None:
        for k, v in weights.items():
            if k in self.task_weights:
                self.task_weights[k] = float(v)

    @staticmethod
    def _relu(x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)

    @staticmethod
    def _softmax(x: np.ndarray) -> np.ndarray:
        e = np.exp(x - np.max(x, axis=1, keepdims=True))
        return e / np.sum(e, axis=1, keepdims=True)

    def _forward_task(self, x: np.ndarray, task_name: str) -> np.ndarray:
        h = self._relu(x @ self.shared_params["W1"] + self.shared_params["b1"])
        return h @ self.task_params[task_name]["W"] + self.task_params[task_name]["b"]

    def _compute_loss(self, logits: np.ndarray, y: np.ndarray) -> float:
        probs = self._softmax(logits)
        y_int = y.astype(int)
        return float(-np.mean(np.log(probs[np.arange(len(y_int)), y_int] + 1e-12)))

    def train_step(self, x: np.ndarray, y: np.ndarray, task_name: str,
                   lr: Optional[float] = None) -> float:
        lr = lr if lr is not None else self.lr
        h = self._relu(x @ self.shared_params["W1"] + self.shared_params["b1"])
        logits = self._forward_task(x, task_name)
        loss = self._compute_loss(logits, y)
        probs = self._softmax(logits)
        y_int = y.astype(int)
        grad = probs.copy()
        grad[np.arange(len(y_int)), y_int] -= 1
        grad /= len(y_int)
        dW_t = h.T @ grad
        db_t = np.sum(grad, axis=0)
        dh = grad @ self.task_params[task_name]["W"].T
        dh = dh * (h > 0)
        dW1 = x.T @ dh
        db1 = np.sum(dh, axis=0)
        self.task_params[task_name]["W"] -= lr * dW_t
        self.task_params[task_name]["b"] -= lr * db_t
        self.shared_params["W1"] -= lr * dW1
        self.shared_params["b1"] -= lr * db1
        self.task_losses.setdefault(task_name, []).append(loss)
        return loss

    def multi_task_train_step(self, batches: Dict[str, Tuple[np.ndarray, np.ndarray]],
                              lr: Optional[float] = None) -> Dict[str, Any]:
        lr = lr if lr is not None else self.lr
        grads_shared = {k: np.zeros_like(v, dtype=np.float64) for k, v in self.shared_params.items()}
        task_losses = {}
        for task_name, (xb, yb) in batches.items():
            if task_name not in self.task_params:
                self.add_task(task_name, int(np.max(yb) + 1) if len(yb) > 0 else 2)
            h = self._relu(xb @ self.shared_params["W1"] + self.shared_params["b1"])
            logits = self._forward_task(xb, task_name)
            loss = self._compute_loss(logits, yb)
            task_losses[task_name] = loss
            probs = self._softmax(logits)
            y_int = yb.astype(int)
            grad = probs.copy()
            grad[np.arange(len(y_int)), y_int] -= 1
            grad /= len(y_int)
            dW_t = h.T @ grad
            db_t = np.sum(grad, axis=0)
            dh = grad @ self.task_params[task_name]["W"].T
            dh = dh * (h > 0)
            dW1 = xb.T @ dh
            db1 = np.sum(dh, axis=0)
            grads_shared["W1"] += dW1
            grads_shared["b1"] += db1
            if self.uncertainty_weighting:
                lv = self.log_vars[task_name]
                grads_shared["W1"] += (1.0 / np.exp(lv)) * dW1 * self.task_weights[task_name]
                grads_shared["b1"] += (1.0 / np.exp(lv)) * db1 * self.task_weights[task_name]
            if self.pc_grad:
                dW1 = dW1 - np.sum(dW1 * grads_shared["W1"]) / (np.sum(grads_shared["W1"] ** 2) + 1e-12)
                db1 = db1 - np.sum(db1 * grads_shared["b1"]) / (np.sum(grads_shared["b1"] ** 2) + 1e-12)
            self.task_params[task_name]["W"] -= lr * dW_t
            self.task_params[task_name]["b"] -= lr * db_t
        for k in self.shared_params:
            self.shared_params[k] -= lr * grads_shared[k]
        total_loss = float(np.mean(list(task_losses.values())))
        self.loss_history.append(total_loss)
        return {"total_loss": total_loss, "task_losses": task_losses}

    def get_task_weights(self) -> Dict[str, float]:
        return dict(self.task_weights)

    def get_multi_task_report(self) -> Dict[str, Any]:
        return {
            "num_tasks": len(self.task_params),
            "total_steps": len(self.loss_history),
            "mean_last_loss": float(np.mean(self.loss_history[-10:])) if len(self.loss_history) >= 10 else (float(self.loss_history[-1]) if self.loss_history else None),
            "task_weights": self.get_task_weights(),
            "per_task_losses": {k: float(np.mean(v)) for k, v in self.task_losses.items()},
        }
