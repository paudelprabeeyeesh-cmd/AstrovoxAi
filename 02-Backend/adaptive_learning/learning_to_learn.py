import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass


@dataclass
class TaskBatch:
    support_x: np.ndarray
    support_y: np.ndarray
    query_x: np.ndarray
    query_y: np.ndarray


class MetaLearner:
    def __init__(self, inner_lr: float = 0.01, outer_lr: float = 0.001, adaptation_steps: int = 5):
        self.inner_lr = inner_lr
        self.outer_lr = outer_lr
        self.adaptation_steps = adaptation_steps
        self.meta_params: Dict[str, np.ndarray] = {}
        self.task_history: List[Dict[str, Any]] = []

    def initialize_params(self, shapes: Dict[str, Tuple[int, ...]]) -> None:
        for name, shape in shapes.items():
            self.meta_params[name] = np.random.randn(*shape).astype(np.float64) * 0.01

    def _forward(self, params: Dict[str, np.ndarray], x: np.ndarray, weights_name: str = "W", bias_name: str = "b") -> np.ndarray:
        W = params[weights_name]
        b = params.get(bias_name, np.zeros(W.shape[1]))
        return x @ W + b

    def adapt_to_task(self, task: TaskBatch, weights_name: str = "W", bias_name: str = "b") -> Dict[str, np.ndarray]:
        adapted = {k: np.array(v) for k, v in self.meta_params.items()}
        x = task.support_x
        for _ in range(self.adaptation_steps):
            logits = self._forward(adapted, x, weights_name, bias_name)
            grad_logits = self._compute_loss_and_grad(logits, task.support_y)
            adapted[weights_name] -= self.inner_lr * (x.T @ grad_logits) / len(x)
            if bias_name in adapted:
                adapted[bias_name] -= self.inner_lr * np.mean(grad_logits, axis=0)
        return adapted

    def meta_update(self, task: TaskBatch, adapted_params: Dict[str, np.ndarray], weights_name: str = "W", bias_name: str = "b") -> None:
        logits = self._forward(adapted_params, task.query_x, weights_name, bias_name)
        grad_logits = self._compute_loss_and_grad(logits, task.query_y)
        x = task.query_x
        self.meta_params[weights_name] -= self.outer_lr * (x.T @ grad_logits) / len(x)
        if bias_name in self.meta_params:
            self.meta_params[bias_name] -= self.outer_lr * np.mean(grad_logits, axis=0)
        loss = float(-np.mean(np.log(self._softmax(logits)[np.arange(len(task.query_y)), task.query_y.astype(int)] + 1e-12)))
        self.task_history.append({"query_loss": loss})

    def _compute_loss_and_grad(self, logits: np.ndarray, y: np.ndarray) -> np.ndarray:
        probs = self._softmax(logits)
        eps = 1e-12
        loss = -np.mean(np.log(probs[np.arange(len(y)), y.astype(int)] + eps))
        grad = probs - np.eye(probs.shape[1])[y.astype(int)]
        grad = grad / len(y)
        return grad

    @staticmethod
    def _softmax(x: np.ndarray) -> np.ndarray:
        e = np.exp(x - np.max(x, axis=1, keepdims=True))
        return e / np.sum(e, axis=1, keepdims=True)

    def meta_train_step(self, tasks: List[TaskBatch], weights_name: str = "W", bias_name: str = "b") -> float:
        total_loss = 0.0
        for task in tasks:
            adapted = self.adapt_to_task(task, weights_name, bias_name)
            self.meta_update(task, adapted, weights_name, bias_name)
            total_loss += self.task_history[-1]["query_loss"]
        return total_loss / max(len(tasks), 1)

    def get_meta_params(self) -> Dict[str, np.ndarray]:
        return {k: np.array(v) for k, v in self.meta_params.items()}
