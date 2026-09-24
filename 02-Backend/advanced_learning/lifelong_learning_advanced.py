import numpy as np
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass


@dataclass
class LifelongConfig:
    input_dim: int
    output_dim: int
    num_tasks: int = 5
    hidden_dim: int = 64
    distillation_temp: float = 2.0
    ewc_lambda: float = 100.0
    max_buffer_size: int = 500


class AdvancedLifelongLearner:
    def __init__(self, config: LifelongConfig):
        self.config = config
        self.params: Dict[str, np.ndarray] = {}
        self.prev_params: Dict[str, np.ndarray] = {}
        self.fisher: Dict[str, np.ndarray] = {}
        self.buffer: List[Tuple[np.ndarray, np.ndarray]] = []
        self.task_count: int = 0
        self.loss_history: List[float] = []
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

    def _compute_loss(self, x: np.ndarray, y: np.ndarray, params: Dict[str, np.ndarray]) -> float:
        logits = self._forward(x, params)
        return float(np.mean((logits - y) ** 2))

    def learn_task(self, x: np.ndarray, y: np.ndarray, steps: int = 10) -> Dict[str, Any]:
        self.prev_params = {k: v.copy() for k, v in self.params.items()}
        lr = 0.01
        for step in range(steps):
            logits = self._forward(x, self.params)
            loss = float(np.mean((logits - y) ** 2))
            if self.task_count > 0 and self.fisher:
                ewc_loss = 0.0
                for k in self.params:
                    if k in self.fisher:
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
        self._update_fisher(x)
        for i in range(min(len(x), self.config.max_buffer_size - len(self.buffer))):
            self.buffer.append((x[i].copy(), y[i].copy()))
        if len(self.buffer) > self.config.max_buffer_size:
            self.buffer = self.buffer[-self.config.max_buffer_size:]
        self.task_count += 1
        self.loss_history.append(loss)
        return {'task_id': self.task_count, 'final_loss': loss}

    def _update_fisher(self, x: np.ndarray) -> None:
        logits = self._forward(x, self.params)
        grad_output = 2.0 * (logits - self._forward(x, self.prev_params)) / x.shape[0]
        h = self._relu(x @ self.params['W1'] + self.params['b1'])
        dh = grad_output @ self.params['W2'].T * self._relu_grad(h)
        self.fisher['W1'] = np.mean(x[:, :, None] * dh[:, None, :], axis=0) ** 2
        self.fisher['b1'] = np.mean(dh ** 2, axis=0)
        self.fisher['W2'] = np.mean(h[:, :, None] * grad_output[:, None, :], axis=0) ** 2
        self.fisher['b2'] = np.mean(grad_output ** 2, axis=0)

    def knowledge_distillation_step(self, x: np.ndarray, old_logits: np.ndarray, lr: float = 0.01) -> Dict[str, Any]:
        new_logits = self._forward(x, self.params)
        soft_targets = np.exp(old_logits / self.config.distillation_temp)
        soft_targets = soft_targets / np.sum(soft_targets, axis=1, keepdims=True)
        soft_preds = np.exp(new_logits / self.config.distillation_temp)
        soft_preds = soft_preds / np.sum(soft_preds, axis=1, keepdims=True)
        kd_loss = float(np.mean(np.sum(soft_targets * np.log(soft_targets / (soft_preds + 1e-12) + 1e-12), axis=1)))
        grad = (soft_preds - soft_targets) / self.config.distillation_temp / x.shape[0]
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
        return {'kd_loss': kd_loss}

    def replay_step(self, batch_size: int = 32, lr: float = 0.01) -> Dict[str, Any]:
        if not self.buffer:
            return {'replay_loss': None}
        indices = np.random.choice(len(self.buffer), size=min(batch_size, len(self.buffer)), replace=False)
        x_batch = np.array([self.buffer[i][0] for i in indices])
        y_batch = np.array([self.buffer[i][1] for i in indices])
        logits = self._forward(x_batch, self.params)
        loss = float(np.mean((logits - y_batch) ** 2))
        grad = 2.0 * (logits - y_batch) / x_batch.shape[0]
        h = self._relu(x_batch @ self.params['W1'] + self.params['b1'])
        db2 = np.sum(grad, axis=0)
        dw2 = h.T @ grad
        dh = grad @ self.params['W2'].T * self._relu_grad(h)
        db1 = np.sum(dh, axis=0)
        dw1 = x_batch.T @ dh
        self.params['W2'] -= lr * dw2
        self.params['b2'] -= lr * db2
        self.params['W1'] -= lr * dw1
        self.params['b1'] -= lr * db1
        return {'replay_loss': loss}

    def get_lifelong_report(self) -> Dict[str, Any]:
        return {
            'tasks_learned': self.task_count,
            'buffer_size': len(self.buffer),
            'last_loss': float(self.loss_history[-1]) if self.loss_history else None,
            'ewc_lambda': self.config.ewc_lambda,
            'distillation_temp': self.config.distillation_temp,
        }
