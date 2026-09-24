import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from .learning_to_learn import MetaLearner, TaskBatch


class LifelongLearning:
    def __init__(self, ewc_lambda: float = 100.0, buffer_size: int = 100, adaptation_steps: int = 5):
        self.ewc_lambda = ewc_lambda
        self.buffer_size = buffer_size
        self.adaptation_steps = adaptation_steps
        self.meta_learner = MetaLearner(inner_lr=0.01, outer_lr=0.001, adaptation_steps=adaptation_steps)
        self.optimal_params: Dict[str, np.ndarray] = {}
        self.fisher_information: Dict[str, np.ndarray] = {}
        self.progressive_columns: Dict[str, Dict[str, np.ndarray]] = {}
        self.seen_tasks: List[str] = []
        self._input_dim: Optional[int] = None
        self._output_dim: int = 2

    def learn_task(self, task_id: str, task: TaskBatch, use_progressive: bool = True) -> Dict[str, Any]:
        if self._input_dim is None:
            self._input_dim = task.support_x.shape[1]
            self._output_dim = max(2, int(np.max(task.support_y)) + 1)
            if not self.meta_learner.meta_params:
                self.meta_learner.initialize_params({
                    "W": (self._input_dim, self._output_dim),
                    "b": (self._output_dim,),
                })
        adapted = self._adapt_with_ewc(task)
        if use_progressive:
            column = self._create_progressive_column(task_id, adapted)
            self.progressive_columns[task_id] = column
        self._update_ewc(task_id, adapted)
        self.seen_tasks.append(task_id)
        logits = self._forward(adapted, task.query_x)
        probs = MetaLearner._softmax(logits)
        y = task.query_y.astype(int)
        loss = float(-np.mean(np.log(probs[np.arange(len(y)), y] + 1e-12)))
        return {"task_id": task_id, "loss": loss, "columns": len(self.progressive_columns)}

    def _adapt_with_ewc(self, task: TaskBatch) -> Dict[str, np.ndarray]:
        params = {k: np.array(v) for k, v in self.meta_learner.meta_params.items()}
        x = task.support_x
        for _ in range(self.adaptation_steps):
            logits = self._forward(params, x)
            grad_logits = self._compute_loss_and_grad(logits, task.support_y)
            for name in params:
                ewc_penalty = self._ewc_penalty(params, name)
                total_grad = grad_logits
                if name == "W":
                    total_grad = (x.T @ grad_logits) / len(x)
                elif name == "b":
                    total_grad = np.mean(grad_logits, axis=0)
                params[name] -= 0.01 * (total_grad + self.ewc_lambda * ewc_penalty)
        return params

    def _create_progressive_column(self, task_id: str, params: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        column: Dict[str, np.ndarray] = {}
        for name, p in params.items():
            col_name = f"{task_id}_{name}"
            column[col_name] = np.array(p)
        return column

    def _update_ewc(self, task_id: str, params: Dict[str, np.ndarray]) -> None:
        self.optimal_params = {k: np.array(v) for k, v in params.items()}
        self.fisher_information = {k: np.ones_like(v) for k, v in params.items()}

    def _ewc_penalty(self, params: Dict[str, np.ndarray], name: str) -> np.ndarray:
        if name not in self.optimal_params:
            return np.zeros_like(params[name])
        diff = params[name] - self.optimal_params[name]
        return self.fisher_information.get(name, np.ones_like(diff)) * diff

    def _forward(self, params: Dict[str, np.ndarray], x: np.ndarray) -> np.ndarray:
        W = params.get("W", np.zeros((x.shape[1], self._output_dim)))
        b = params.get("b", np.zeros(self._output_dim))
        return x @ W + b

    def _compute_loss_and_grad(self, logits: np.ndarray, y: np.ndarray) -> np.ndarray:
        probs = MetaLearner._softmax(logits)
        grad = probs - np.eye(probs.shape[1])[y.astype(int)]
        return grad / len(y)

    def get_lifelong_report(self) -> Dict[str, Any]:
        return {
            "num_tasks": len(self.seen_tasks),
            "tasks": self.seen_tasks,
            "columns": len(self.progressive_columns),
            "ewc_lambda": self.ewc_lambda,
        }
