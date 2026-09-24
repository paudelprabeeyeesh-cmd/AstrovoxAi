import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field


@dataclass
class TaskBatch:
    support_x: np.ndarray
    support_y: np.ndarray
    query_x: np.ndarray
    query_y: np.ndarray
    task_id: str = "task"


class AdvancedContinualLearner:
    def __init__(self, input_dim: int, hidden_dim: int = 64, num_classes: int = 5,
                 lr: float = 0.01, ewc_lambda: float = 100.0, buffer_size: int = 100,
                 replay_alpha: float = 0.5, lwf_lambda: float = 1.0):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_classes = num_classes
        self.lr = lr
        self.ewc_lambda = ewc_lambda
        self.buffer_size = buffer_size
        self.replay_alpha = replay_alpha
        self.lwf_lambda = lwf_lambda
        self.params: Dict[str, np.ndarray] = {}
        self.fisher: Dict[str, np.ndarray] = {}
        self.prev_params: Dict[str, np.ndarray] = {}
        self.replay_buffer: List[TaskBatch] = []
        self.seen_tasks: List[str] = []
        self.task_logits: Dict[str, np.ndarray] = {}
        self.loss_history: List[float] = []
        self.task_losses: Dict[str, List[float]] = {}
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

    def _forward(self, x: np.ndarray, params: Optional[Dict[str, np.ndarray]] = None) -> Tuple[np.ndarray, np.ndarray]:
        p = params if params is not None else self.params
        h = self._relu(x @ p["W1"] + p["b1"])
        logits = h @ p["W2"] + p["b2"]
        return h, logits

    def _compute_loss(self, logits: np.ndarray, y: np.ndarray) -> float:
        probs = self._softmax(logits)
        y_int = y.astype(int)
        return float(-np.mean(np.log(probs[np.arange(len(y_int)), y_int] + 1e-12)))

    def _build_train_batch(self, task: TaskBatch, use_replay: bool, use_lwf: bool) -> Tuple[np.ndarray, np.ndarray]:
        batch_x = task.support_x
        batch_y = task.support_y
        if use_replay and self.replay_buffer:
            n = int(self.replay_alpha * len(task.support_x))
            indices = np.random.choice(len(self.replay_buffer), size=min(n, len(self.replay_buffer)), replace=False)
            for i in indices:
                buf = self.replay_buffer[int(i)]
                batch_x = np.vstack([batch_x, buf.support_x])
                batch_y = np.concatenate([batch_y, buf.support_y])
        return batch_x, batch_y

    def _ewc_penalty(self) -> float:
        penalty = 0.0
        for k in self.params:
            penalty += float(np.sum(self.fisher.get(k, 0.0) * (self.params[k] - self.prev_params.get(k, 0.0)) ** 2))
        return penalty

    def _lwf_penalty(self, x: np.ndarray) -> float:
        if not self.task_logits:
            return 0.0
        _, logits = self._forward(x)
        penalty = 0.0
        for old_logits in self.task_logits.values():
            penalty += float(np.mean((self._softmax(logits) - self._softmax(old_logits)) ** 2))
        return penalty / max(1, len(self.task_logits))

    def learn_task(self, task: TaskBatch, use_replay: bool = True, use_ewc: bool = True,
                   use_lwf: bool = True) -> Dict[str, Any]:
        task_loss = 0.0
        num_steps = 5
        for _ in range(num_steps):
            batch_x, batch_y = self._build_train_batch(task, use_replay, use_lwf)
            _, logits = self._forward(batch_x)
            ce_loss = self._compute_loss(logits, batch_y)
            ewc_loss = self._ewc_penalty() if use_ewc and self.fisher else 0.0
            lwf_loss = self._lwf_penalty(batch_x) if use_lwf and self.task_logits else 0.0
            loss = ce_loss + self.ewc_lambda * ewc_loss + self.lwf_lambda * lwf_loss
            task_loss += loss
            self.loss_history.append(loss)
            h = self._relu(batch_x @ self.params["W1"] + self.params["b1"])
            probs = self._softmax(logits)
            y_int = batch_y.astype(int)
            grad = probs.copy()
            grad[np.arange(len(y_int)), y_int] -= 1
            grad /= len(y_int)
            dW2 = h.T @ grad
            db2 = np.sum(grad, axis=0)
            dh = grad @ self.params["W2"].T
            dh = dh * (h > 0)
            dW1 = batch_x.T @ dh
            db1 = np.sum(dh, axis=0)
            for k in self.params:
                g = {"W1": dW1, "b1": db1, "W2": dW2, "b2": db2}[k]
                self.params[k] -= self.lr * (g - self.ewc_lambda * self.fisher.get(k, 0.0) * (self.params[k] - self.prev_params.get(k, 0.0)))
        self.task_logits[task.task_id] = logits
        self._update_fisher(batch_x)
        self._store_replay(task)
        self.seen_tasks.append(task.task_id)
        self.task_losses.setdefault(task.task_id, []).append(task_loss / num_steps)
        return {"task_id": task.task_id, "loss": float(task_loss / num_steps), "buffer_size": len(self.replay_buffer)}

    def _update_fisher(self, x: np.ndarray) -> None:
        self.prev_params = {k: v.copy() for k, v in self.params.items()}
        self.fisher = {k: np.zeros_like(v, dtype=np.float64) for k, v in self.params.items()}
        n = min(100, len(x))
        indices = np.random.choice(len(x), size=n, replace=False)
        x_sample = x[indices]
        h, logits = self._forward(x_sample)
        probs = self._softmax(logits)
        for i in range(len(x_sample)):
            loss = -np.sum(np.log(probs[i] + 1e-12))
            h_i = h[i:i+1]
            dW2 = h_i.T @ (probs[i:i+1])
            db2 = np.sum(probs[i:i+1], axis=0)
            dh = (probs[i:i+1]) @ self.params["W2"].T
            dh = dh * (h_i > 0)
            dW1 = x_sample[i:i+1].T @ dh
            db1 = np.sum(dh, axis=0)
            self.fisher["W1"] += np.sum(dW1 ** 2, axis=1, keepdims=True)
            self.fisher["b1"] += db1 ** 2
            self.fisher["W2"] += np.sum(dW2 ** 2, axis=1, keepdims=True)
            self.fisher["b2"] += db2 ** 2
        for k in self.fisher:
            self.fisher[k] = np.clip(self.fisher[k] / n, 1e-10, None)

    def _store_replay(self, task: TaskBatch) -> None:
        self.replay_buffer.append(task)
        if len(self.replay_buffer) > self.buffer_size:
            self.replay_buffer.pop(0)

    def evaluate_task(self, task: TaskBatch) -> Dict[str, Any]:
        _, logits = self._forward(task.query_x)
        loss = self._compute_loss(logits, task.query_y)
        probs = self._softmax(logits)
        preds = np.argmax(probs, axis=1)
        acc = float(np.mean(preds == task.query_y.astype(int)))
        return {"loss": loss, "accuracy": acc, "predictions": preds}

    def forget_free_metric(self) -> float:
        if len(self.loss_history) < 10:
            return 0.0
        return float(np.std(self.loss_history[-10:]) / (np.mean(self.loss_history[-10:]) + 1e-12))

    def get_continual_report(self) -> Dict[str, Any]:
        return {
            "num_tasks": len(self.seen_tasks),
            "buffer_size": len(self.replay_buffer),
            "total_steps": len(self.loss_history),
            "mean_last_loss": float(np.mean(self.loss_history[-10:])) if len(self.loss_history) >= 10 else (float(self.loss_history[-1]) if self.loss_history else None),
            "forget_free_metric": self.forget_free_metric(),
            "task_losses": {k: float(np.mean(v)) for k, v in self.task_losses.items()},
        }
