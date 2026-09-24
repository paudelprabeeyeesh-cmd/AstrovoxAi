import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field


@dataclass
class ContinualConfig:
    input_dim: int
    output_dim: int
    num_tasks: int = 3
    hidden_dim: int = 64
    ewc_lambda: float = 100.0
    replay_ratio: float = 0.3
    max_replay_size: int = 200


class AdvancedContinualLearner:
    def __init__(self, config: ContinualConfig):
        self.config = config
        self.params: Dict[str, np.ndarray] = {}
        self.task_params: Dict[int, Dict[str, np.ndarray]] = {}
        self.prev_params: Dict[str, np.ndarray] = {}
        self.fisher: Dict[str, np.ndarray] = {}
        self.replay_buffer: List[Tuple[np.ndarray, np.ndarray, int]] = []
        self.current_task: int = 0
        self.loss_history: List[float] = []
        self.task_boundaries: List[int] = []
        self._initialize_params()

    def _initialize_params(self) -> None:
        self.params['W1'] = np.random.randn(self.config.input_dim, self.config.hidden_dim).astype(np.float64) * np.sqrt(2.0 / self.config.input_dim)
        self.params['b1'] = np.zeros(self.config.hidden_dim, dtype=np.float64)
        self.params['W2'] = np.random.randn(self.config.hidden_dim, self.config.output_dim).astype(np.float64) * np.sqrt(2.0 / self.config.hidden_dim)
        self.params['b2'] = np.zeros(self.config.output_dim, dtype=np.float64)

    @staticmethod
    def _relu(x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)

    @staticmethod
    def _relu_grad(x: np.ndarray) -> np.ndarray:
        return (x > 0).astype(np.float64)

    def _forward(self, x: np.ndarray, params: Dict[str, np.ndarray]) -> np.ndarray:
        h = self._relu(x @ params['W1'] + params['b1'])
        return h @ params['W2'] + params['b2']

    def start_task(self, task_id: int) -> None:
        self.current_task = task_id
        self.prev_params = {k: v.copy() for k, v in self.params.items()}
        self.task_boundaries.append(len(self.loss_history))

    def _update_fisher(self, x: np.ndarray) -> None:
        logits = self._forward(x, self.params)
        grad_output = 2.0 * (logits - self._forward(x, self.prev_params)) / x.shape[0]
        h = self._relu(x @ self.params['W1'] + self.params['b1'])
        dh = grad_output @ self.params['W2'].T * self._relu_grad(h)
        self.fisher['W1'] = np.mean(x[:, :, None] * dh[:, None, :], axis=0) ** 2
        self.fisher['b1'] = np.mean(dh ** 2, axis=0)
        self.fisher['W2'] = np.mean(h[:, :, None] * grad_output[:, None, :], axis=0) ** 2
        self.fisher['b2'] = np.mean(grad_output ** 2, axis=0)

    def train_step(self, x: np.ndarray, y: np.ndarray, lr: float = 0.01) -> Dict[str, Any]:
        logits = self._forward(x, self.params)
        loss = float(np.mean((logits - y) ** 2))
        if self.current_task > 0 and self.fisher:
            ewc_loss = 0.0
            for k in self.params:
                if k in self.fisher and k in self.prev_params:
                    diff = self.params[k] - self.prev_params[k]
                    ewc_loss += float(np.sum(self.fisher[k] * (diff ** 2)))
            loss += 0.5 * self.config.ewc_lambda * ewc_loss
        grad = 2.0 * (logits - y) / x.shape[0]
        h = self._relu(x @ self.params['W1'] + self.params['b1'])
        db2 = np.sum(grad, axis=0)
        dw2 = h.T @ grad
        dh = grad @ self.params['W2'].T * self._relu_grad(h)
        db1 = np.sum(dh, axis=0)
        dw1 = x.T @ dh
        self.params['W2'] -= lr * dw2
        self.params['b2'] -= lr * db2
        self.params['W1'] -= lr * dw1
        self.params['b1'] -= lr * db1
        replay_x = self._sample_replay(int(len(x) * self.config.replay_ratio))
        if len(replay_x) > 0:
            replay_y = np.array([r[1] for r in replay_x])
            replay_x_arr = np.array([r[0] for r in replay_x])
            logits_r = self._forward(replay_x_arr, self.params)
            replay_loss = float(np.mean((logits_r - replay_y) ** 2))
            loss = loss * 0.7 + replay_loss * 0.3
        self.loss_history.append(loss)
        for i in range(len(x)):
            self.replay_buffer.append((x[i].copy(), y[i].copy(), self.current_task))
        if len(self.replay_buffer) > self.config.max_replay_size:
            self.replay_buffer = self.replay_buffer[-self.config.max_replay_size:]
        return {'loss': loss, 'task_id': self.current_task}

    def _sample_replay(self, n: int) -> List[Tuple[np.ndarray, np.ndarray, int]]:
        if not self.replay_buffer:
            return []
        indices = np.random.choice(len(self.replay_buffer), size=min(n, len(self.replay_buffer)), replace=False)
        return [self.replay_buffer[i] for i in indices]

    def evaluate_task(self, x: np.ndarray, y: np.ndarray, task_id: Optional[int] = None) -> Dict[str, float]:
        logits = self._forward(x, self.params)
        loss = float(np.mean((logits - y) ** 2))
        return {'task_loss': loss, 'task_id': task_id if task_id is not None else self.current_task}

    def get_continual_report(self) -> Dict[str, Any]:
        return {
            'current_task': self.current_task,
            'tasks_encountered': len(self.task_boundaries),
            'replay_buffer_size': len(self.replay_buffer),
            'last_loss': float(self.loss_history[-1]) if self.loss_history else None,
            'ewc_lambda': self.config.ewc_lambda,
            'replay_ratio': self.config.replay_ratio,
            'task_boundaries': self.task_boundaries,
        }
