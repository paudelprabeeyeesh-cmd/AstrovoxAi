import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import copy


@dataclass
class MetaConfig:
    input_dim: int
    output_dim: int
    inner_lr: float = 0.01
    meta_lr: float = 0.001
    num_inner_steps: int = 5
    num_tasks: int = 4
    hidden_dim: int = 64


class AdvancedMetaLearner:
    def __init__(self, config: MetaConfig):
        self.config = config
        self.params: Dict[str, np.ndarray] = {}
        self.meta_history: List[Dict[str, Any]] = []
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

    def _adapt(self, x: np.ndarray, y: np.ndarray, params: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        adapted = {k: v.copy() for k, v in params.items()}
        lr = self.config.inner_lr
        for _ in range(self.config.num_inner_steps):
            logits = self._forward(x, adapted)
            loss = float(np.mean((logits - y) ** 2))
            grad = 2.0 * (logits - y) / x.shape[0]
            h = self._relu(x @ adapted['W1'] + adapted['b1'])
            db2 = np.sum(grad, axis=0)
            dw2 = h.T @ grad
            dh = grad @ adapted['W2'].T * self._relu_grad(h)
            db1 = np.sum(dh, axis=0)
            dw1 = x.T @ dh
            adapted['W2'] -= lr * dw2
            adapted['b2'] -= lr * db2
            adapted['W1'] -= lr * dw1
            adapted['b1'] -= lr * db1
        return adapted

    def sample_task(self, num_samples: int = 20) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        x_support = np.random.randn(num_samples, self.config.input_dim).astype(np.float64)
        y_support = np.random.randn(num_samples, self.config.output_dim).astype(np.float64)
        x_query = np.random.randn(num_samples, self.config.input_dim).astype(np.float64)
        y_query = np.random.randn(num_samples, self.config.output_dim).astype(np.float64)
        return x_support, y_support, x_query, y_query

    def meta_train_step(self) -> Dict[str, Any]:
        meta_grad: Dict[str, np.ndarray] = {k: np.zeros_like(v) for k, v in self.params.items()}
        meta_loss = 0.0
        for _ in range(self.config.num_tasks):
            x_s, y_s, x_q, y_q = self.sample_task()
            adapted = self._adapt(x_s, y_s, self.params)
            q_loss = self._compute_loss(x_q, y_q, adapted)
            meta_loss += q_loss
            grad = 2.0 * (self._forward(x_q, adapted) - y_q) / x_q.shape[0]
            h = self._relu(x_q @ adapted['W1'] + adapted['b1'])
            db2 = np.sum(grad, axis=0)
            dw2 = h.T @ grad
            dh = grad @ adapted['W2'].T * self._relu_grad(h)
            db1 = np.sum(dh, axis=0)
            dw1 = x_q.T @ dh
            meta_grad['W2'] += dw2
            meta_grad['b2'] += db2
            meta_grad['W1'] += dw1
            meta_grad['b1'] += db1
        for k in self.params:
            self.params[k] -= self.config.meta_lr * meta_grad[k] / self.config.num_tasks
        meta_loss /= self.config.num_tasks
        self.meta_history.append({'loss': meta_loss})
        return {'meta_loss': meta_loss}

    def adapt(self, x_support: np.ndarray, y_support: np.ndarray) -> Dict[str, np.ndarray]:
        return self._adapt(x_support, y_support, self.params)

    def evaluate(self, x_query: np.ndarray, y_query: np.ndarray, adapted_params: Optional[Dict[str, np.ndarray]] = None) -> Dict[str, float]:
        params = adapted_params if adapted_params is not None else self.params
        logits = self._forward(x_query, params)
        loss = float(np.mean((logits - y_query) ** 2))
        return {'query_loss': loss}

    def get_meta_report(self) -> Dict[str, Any]:
        return {
            'num_meta_steps': len(self.meta_history),
            'last_meta_loss': float(self.meta_history[-1]['loss']) if self.meta_history else None,
            'mean_meta_loss': float(np.mean([m['loss'] for m in self.meta_history[-10:]])) if len(self.meta_history) >= 10 else (float(self.meta_history[-1]['loss']) if self.meta_history else None),
            'inner_lr': self.config.inner_lr,
            'meta_lr': self.config.meta_lr,
            'num_inner_steps': self.config.num_inner_steps,
        }
