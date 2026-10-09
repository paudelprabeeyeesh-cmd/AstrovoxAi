import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass


@dataclass
class SSLConfig:
    input_dim: int
    projection_dim: int = 128
    temperature: float = 0.07
    queue_size: int = 4096
    momentum: float = 0.999
    mask_ratio: float = 0.15


class AdvancedSelfSupervisedLearner:
    def __init__(self, config: SSLConfig):
        self.config = config
        self.params: Dict[str, np.ndarray] = {}
        self.momentum_params: Dict[str, np.ndarray] = {}
        self.queue: Optional[np.ndarray] = None
        self.queue_ptr: int = 0
        self.loss_history: List[float] = []
        self._initialize_params()

    def _initialize_params(self) -> None:
        d = self.config.input_dim
        p = self.config.projection_dim
        self.params['W1'] = np.random.randn(d, d).astype(np.float64) * np.sqrt(2.0 / d)
        self.params['b1'] = np.zeros(d, dtype=np.float64)
        self.params['W2'] = np.random.randn(d, d).astype(np.float64) * np.sqrt(2.0 / d)
        self.params['b2'] = np.zeros(d, dtype=np.float64)
        self.params['Wp'] = np.random.randn(d, p).astype(np.float64) * np.sqrt(2.0 / d)
        self.params['bp'] = np.zeros(p, dtype=np.float64)
        self.momentum_params = {k: v.copy() for k, v in self.params.items()}

    @staticmethod
    def _relu(x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)

    @staticmethod
    def _relu_grad(x: np.ndarray) -> np.ndarray:
        return (x > 0).astype(np.float64)

    @staticmethod
    def _softmax(x: np.ndarray) -> np.ndarray:
        e = np.exp(x - np.max(x, axis=1, keepdims=True))
        return e / np.sum(e, axis=1, keepdims=True)

    def _encode(self, x: np.ndarray, params: Dict[str, np.ndarray]) -> np.ndarray:
        h = self._relu(x @ params['W1'] + params['b1'])
        h = self._relu(h @ params['W2'] + params['b2'])
        return h @ params['Wp'] + params['bp']

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        a_norm = np.linalg.norm(a, axis=1, keepdims=True) + 1e-12
        b_norm = np.linalg.norm(b, axis=1, keepdims=True) + 1e-12
        return (a @ b.T) / (a_norm @ b_norm.T)

    def _nt_xent_loss(self, z_i: np.ndarray, z_j: np.ndarray, queue: Optional[np.ndarray] = None) -> float:
        z_i = z_i / (np.linalg.norm(z_i, axis=1, keepdims=True) + 1e-12)
        z_j = z_j / (np.linalg.norm(z_j, axis=1, keepdims=True) + 1e-12)
        N = len(z_i)
        l_pos = np.sum(z_i * z_j, axis=1)
        if queue is not None and len(queue) > 0:
            l_neg = z_i @ queue.T
        else:
            l_neg = z_i @ z_j.T
        logits = np.concatenate([l_pos[:, None], l_neg], axis=1) / self.config.temperature
        labels = np.zeros(N, dtype=int)
        probs = self._softmax(logits)
        loss = float(-np.mean(np.log(probs[np.arange(N), labels] + 1e-12)))
        return loss

    def _build_queue(self, batch_size: int) -> np.ndarray:
        if self.queue is None:
            self.queue = np.random.randn(self.config.queue_size, self.config.projection_dim).astype(np.float64) * 0.01
            self.queue_ptr = 0
            return self.queue
        if len(self.queue) < self.config.queue_size:
            return self.queue
        ptr = self.queue_ptr % self.config.queue_size
        end = min(ptr + batch_size, self.config.queue_size)
        actual = end - ptr
        if actual > 0:
            self.queue[ptr:end] = np.random.randn(actual, self.config.projection_dim).astype(np.float64) * 0.01
        self.queue_ptr = (ptr + batch_size) % self.config.queue_size
        return self.queue

    def mask_and_reconstruct(self, x: np.ndarray, mask_ratio: Optional[float] = None) -> Tuple[np.ndarray, np.ndarray]:
        mr = mask_ratio if mask_ratio is not None else self.config.mask_ratio
        B, D = x.shape
        num_masked = max(1, int(D * mr))
        mask = np.random.permutation(D)[:num_masked]
        x_masked = x.copy()
        x_masked[:, mask] = 0.0
        target = x[:, mask]
        return x_masked, target

    def train_step(self, x: np.ndarray, x_aug: Optional[np.ndarray] = None) -> Dict[str, Any]:
        if x_aug is None:
            x_aug = x + np.random.randn(*x.shape).astype(np.float64) * 0.01
        z_i = self._encode(x, self.params)
        z_j = self._encode(x_aug, self.momentum_params)
        queue = self._build_queue(len(x))
        loss = self._nt_xent_loss(z_i, z_j, queue=queue)
        self.loss_history.append(loss)
        z_norm = z_i / (np.linalg.norm(z_i, axis=1, keepdims=True) + 1e-12)
        if len(queue) >= len(z_norm):
            queue[:len(z_norm)] = queue[:len(z_norm)] * self.config.momentum + z_norm * (1.0 - self.config.momentum)
        lr = 0.01
        h = self._relu(x @ self.params['W1'] + self.params['b1'])
        h2 = self._relu(h @ self.params['W2'] + self.params['b2'])
        zj = self._relu(x_aug @ self.momentum_params['W1'] + self.momentum_params['b1'])
        zj2 = self._relu(zj @ self.momentum_params['W2'] + self.momentum_params['b2'])
        neg_keys = queue if queue is not None else z_j
        batch_size = len(x)
        logits = (z_i @ np.vstack([zj2, neg_keys[:max(0, self.config.queue_size - batch_size)]]).T) / self.config.temperature
        logits = np.concatenate([np.sum(z_i * zj2, axis=1, keepdims=True), logits], axis=1)
        probs = self._softmax(logits)
        grad = probs.copy()
        grad[np.arange(batch_size), 0] -= 1
        grad /= batch_size
        dWp = h2.T @ grad[:, :1]
        dbp = np.sum(grad[:, :1], axis=0)
        dh = grad[:, :1] @ self.params['Wp'].T
        dh = dh * self._relu_grad(h2)
        dh2 = dh @ self.params['W2'].T * self._relu_grad(h)
        dW1 = x.T @ dh2
        db1 = np.sum(dh2, axis=0)
        dW2 = h.T @ dh
        db2 = np.sum(dh, axis=0)
        self.params['Wp'] -= lr * dWp
        self.params['bp'] -= lr * dbp
        self.params['W1'] -= lr * dW1
        self.params['b1'] -= lr * db1
        self.params['W2'] -= lr * dW2
        self.params['b2'] -= lr * db2
        for k in self.momentum_params:
            self.momentum_params[k] = self.config.momentum * self.momentum_params[k] + (1.0 - self.config.momentum) * self.params[k]
        return {
            'loss': loss,
            'temperature': self.config.temperature,
            'queue_len': len(self.queue) if self.queue is not None else 0,
        }

    def contrastive_loss(self, z_i: np.ndarray, z_j: np.ndarray) -> float:
        return self._nt_xent_loss(z_i, z_j)

    def evaluate(self, x: np.ndarray, x_pos: np.ndarray, x_neg: np.ndarray) -> Dict[str, float]:
        z = self._encode(x, self.params)
        z_pos = self._encode(x_pos, self.params)
        z_neg = self._encode(x_neg, self.params)
        pos = np.sum((z - z_pos) ** 2, axis=1)
        neg = np.sum((z[:, None, :] - z_neg[None, :, :]) ** 2, axis=2)
        margin = 0.2
        loss = float(np.mean(np.maximum(margin + pos[:, None] - neg, 0)))
        return {'triplet_loss': loss}

    def get_ssl_report(self) -> Dict[str, Any]:
        return {
            'num_steps': len(self.loss_history),
            'last_loss': float(self.loss_history[-1]) if self.loss_history else None,
            'mean_loss': float(np.mean(self.loss_history[-10:])) if len(self.loss_history) >= 10 else (float(self.loss_history[-1]) if self.loss_history else None),
            'temperature': self.config.temperature,
            'queue_size': len(self.queue) if self.queue is not None else 0,
            'queue_capacity': self.config.queue_size,
            'momentum': self.config.momentum,
            'mask_ratio': self.config.mask_ratio,
        }
