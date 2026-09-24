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


class OnlineMAML:
    def __init__(self, input_dim: int = 32, hidden_dim: int = 64, output_dim: int = 5,
                 inner_lr: float = 0.01, outer_lr: float = 0.001, adaptation_steps: int = 5,
                 num_tasks: int = 16, num_query: int = 8):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.inner_lr = inner_lr
        self.outer_lr = outer_lr
        self.adaptation_steps = adaptation_steps
        self.num_tasks = num_tasks
        self.num_query = num_query
        self.params: Dict[str, np.ndarray] = {}
        self._initialize_params()
        self.task_losses: List[float] = []
        self.step_losses: List[float] = []

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

    def _forward(self, x: np.ndarray, params: Dict[str, np.ndarray]) -> np.ndarray:
        h = self._relu(x @ params["W1"] + params["b1"])
        return h @ params["W2"] + params["b2"]

    def _compute_loss(self, logits: np.ndarray, y: np.ndarray) -> float:
        probs = self._softmax(logits)
        y_int = y.astype(int)
        return float(-np.mean(np.log(probs[np.arange(len(y_int)), y_int] + 1e-12)))

    def _compute_gradients(self, logits: np.ndarray, y: np.ndarray, x: np.ndarray, h: np.ndarray,
                           params: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        probs = self._softmax(logits)
        y_int = y.astype(int)
        batch_size = len(y_int)
        grad = probs.copy()
        grad[np.arange(batch_size), y_int] -= 1
        grad /= batch_size
        dW2 = h.T @ grad
        db2 = np.sum(grad, axis=0)
        dh = grad @ params["W2"].T
        dh = dh * (h > 0)
        dW1 = x.T @ dh
        db1 = np.sum(dh, axis=0)
        return {"W1": dW1, "b1": db1, "W2": dW2, "b2": db2}

    def adapt(self, x: np.ndarray, y: np.ndarray, steps: int = -1) -> Dict[str, np.ndarray]:
        steps = self.adaptation_steps if steps < 0 else steps
        params = {k: v.copy() for k, v in self.params.items()}
        for _ in range(steps):
            logits = self._forward(x, params)
            loss = self._compute_loss(logits, y)
            h = self._relu(x @ params["W1"] + params["b1"])
            grads = self._compute_gradients(logits, y, x, h, params)
            for k in params:
                params[k] = params[k] - self.inner_lr * grads[k]
        return params

    def meta_train_step(self, tasks: List[Episode]) -> float:
        meta_grads: Dict[str, np.ndarray] = {}
        total_loss = 0.0
        for task in tasks:
            adapted = self.adapt(task.support_x, task.support_y)
            logits = self._forward(task.query_x, adapted)
            loss = self._compute_loss(logits, task.query_y)
            total_loss += loss
            h = self._relu(task.query_x @ adapted["W1"] + adapted["b1"])
            grads = self._compute_gradients(logits, task.query_y, task.query_x, h, adapted)
            for k in grads:
                meta_grads[k] = meta_grads.get(k, 0.0) + grads[k]
        self.task_losses.append(total_loss / max(1, len(tasks)))
        self._update_meta_params(meta_grads, len(tasks))
        return total_loss / max(1, len(tasks))

    def _update_meta_params(self, meta_grads: Dict[str, np.ndarray], num_tasks: int) -> None:
        for k in self.params:
            self.params[k] = self.params[k] - self.outer_lr * meta_grads[k] / num_tasks

    def online_step(self, x: np.ndarray, y: np.ndarray) -> float:
        params = self.adapt(x, y, steps=1)
        logits = self._forward(x, params)
        loss = self._compute_loss(logits, y)
        self.params = params
        self.step_losses.append(loss)
        return loss

    def evaluate_episode(self, episode: Episode) -> Dict[str, Any]:
        adapted = self.adapt(episode.support_x, episode.support_y)
        logits = self._forward(episode.query_x, adapted)
        probs = self._softmax(logits)
        preds = np.argmax(probs, axis=1)
        loss = self._compute_loss(logits, episode.query_y)
        acc = float(np.mean(preds == episode.query_y.astype(int)))
        return {"loss": loss, "accuracy": acc, "predictions": preds, "probs": probs}

    def get_training_report(self) -> Dict[str, Any]:
        return {
            "num_meta_steps": len(self.task_losses),
            "num_online_steps": len(self.step_losses),
            "last_meta_loss": float(self.task_losses[-1]) if self.task_losses else None,
            "last_online_loss": float(self.step_losses[-1]) if self.step_losses else None,
            "mean_meta_loss": float(np.mean(self.task_losses)) if self.task_losses else None,
        }


class FastAdaptationModel:
    def __init__(self, input_dim: int = 32, hidden_dim: int = 64, num_classes: int = 5,
                 lr: float = 0.01, steps: int = 10):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_classes = num_classes
        self.lr = lr
        self.steps = steps
        self.params: Dict[str, np.ndarray] = {}
        self.loss_history: List[float] = []
        self._initialize_params()

    def _initialize_params(self) -> None:
        self.params["W1"] = np.random.randn(self.input_dim, self.hidden_dim).astype(np.float64) * 0.1
        self.params["b1"] = np.zeros(self.hidden_dim, dtype=np.float64)
        self.params["W2"] = np.random.randn(self.hidden_dim, self.num_classes).astype(np.float64) * 0.1
        self.params["b2"] = np.zeros(self.num_classes, dtype=np.float64)

    @staticmethod
    def _relu(x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)

    @staticmethod
    def _softmax(x: np.ndarray) -> np.ndarray:
        e = np.exp(x - np.max(x, axis=1, keepdims=True))
        return e / np.sum(e, axis=1, keepdims=True)

    def _forward(self, x: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        h = self._relu(x @ self.params["W1"] + self.params["b1"])
        logits = h @ self.params["W2"] + self.params["b2"]
        return h, logits

    def _loss(self, logits: np.ndarray, y: np.ndarray) -> float:
        probs = self._softmax(logits)
        y_int = y.astype(int)
        return float(-np.mean(np.log(probs[np.arange(len(y_int)), y_int] + 1e-12)))

    def adapt(self, support_x: np.ndarray, support_y: np.ndarray) -> Dict[str, np.ndarray]:
        for _ in range(self.steps):
            h, logits = self._forward(support_x)
            loss = self._loss(logits, support_y)
            self.loss_history.append(loss)
            probs = self._softmax(logits)
            y_int = support_y.astype(int)
            grad = probs.copy()
            grad[np.arange(len(y_int)), y_int] -= 1
            grad /= len(y_int)
            dW2 = h.T @ grad
            db2 = np.sum(grad, axis=0)
            dh = grad @ self.params["W2"].T
            dh = dh * (h > 0)
            dW1 = support_x.T @ dh
            db1 = np.sum(dh, axis=0)
            self.params["W1"] -= self.lr * dW1
            self.params["b1"] -= self.lr * db1
            self.params["W2"] -= self.lr * dW2
            self.params["b2"] -= self.lr * db2
        return {k: v.copy() for k, v in self.params.items()}

    def predict(self, query_x: np.ndarray) -> np.ndarray:
        _, logits = self._forward(query_x)
        probs = self._softmax(logits)
        return np.argmax(probs, axis=1)

    def get_adaptation_report(self) -> Dict[str, Any]:
        return {
            "steps": len(self.loss_history),
            "initial_loss": float(self.loss_history[0]) if self.loss_history else None,
            "final_loss": float(self.loss_history[-1]) if self.loss_history else None,
            "min_loss": float(np.min(self.loss_history)) if self.loss_history else None,
        }
