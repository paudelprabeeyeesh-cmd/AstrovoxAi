import numpy as np
from typing import Dict, List, Optional, Tuple, Any


class AdvancedSelfSupervisedLearner:
    def __init__(self, input_dim: int, projection_dim: int = 128, temperature: float = 0.07,
                 queue_size: int = 4096, momentum: float = 0.999):
        self.input_dim = input_dim
        self.projection_dim = projection_dim
        self.temperature = temperature
        self.queue_size = queue_size
        self.momentum = momentum
        self.params: Dict[str, np.ndarray] = {}
        self.momentum_params: Dict[str, np.ndarray] = {}
        self.queue: Optional[np.ndarray] = None
        self.loss_history: List[float] = []
        self._initialized: bool = False
        self._initialize_params()

    def _initialize_params(self) -> None:
        self.params["W1"] = np.random.randn(self.input_dim, self.input_dim).astype(np.float64) * 0.1
        self.params["b1"] = np.zeros(self.input_dim, dtype=np.float64)
        self.params["Wp"] = np.random.randn(self.input_dim, self.projection_dim).astype(np.float64) * 0.1
        self.params["bp"] = np.zeros(self.projection_dim, dtype=np.float64)
        self.momentum_params = {k: v.copy() for k, v in self.params.items()}

    @staticmethod
    def _relu(x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)

    @staticmethod
    def _softmax(x: np.ndarray) -> np.ndarray:
        e = np.exp(x - np.max(x, axis=1, keepdims=True))
        return e / np.sum(e, axis=1, keepdims=True)

    def _encode(self, x: np.ndarray, params: Dict[str, np.ndarray]) -> np.ndarray:
        h = self._relu(x @ params["W1"] + params["b1"])
        return h @ params["Wp"] + params["bp"]

    def _nt_xent_loss(self, z_i: np.ndarray, z_j: np.ndarray, queue: Optional[np.ndarray] = None) -> float:
        z_i = z_i / (np.linalg.norm(z_i, axis=1, keepdims=True) + 1e-12)
        z_j = z_j / (np.linalg.norm(z_j, axis=1, keepdims=True) + 1e-12)
        l_pos = np.sum(z_i * z_j, axis=1)
        l_neg = z_i @ (queue.T if queue is not None else z_j.T)
        logits = np.concatenate([l_pos[:, None], l_neg], axis=1) / self.temperature
        labels = np.zeros(len(logits), dtype=int)
        loss = float(-np.mean(np.log(self._softmax(logits)[np.arange(len(labels)), labels] + 1e-12)))
        return loss

    def _build_queue(self, batch_size: int) -> np.ndarray:
        if self.queue is None:
            self.queue = np.random.randn(self.queue_size, self.projection_dim).astype(np.float64) * 0.01
            return self.queue
        if len(self.queue) < self.queue_size:
            return self.queue
        self.queue = np.vstack([self.queue[batch_size:], np.random.randn(batch_size, self.projection_dim).astype(np.float64) * 0.01])
        return self.queue

    def train_step(self, x: np.ndarray, x_aug: np.ndarray) -> Dict[str, Any]:
        z_i = self._encode(x, self.params)
        z_j = self._encode(x_aug, self.momentum_params)
        queue = self._build_queue(len(x))
        loss = self._nt_xent_loss(z_i, z_j, queue=queue)
        self.loss_history.append(loss)
        z_norm = z_i / (np.linalg.norm(z_i, axis=1, keepdims=True) + 1e-12)
        queue[:len(z_norm)] = queue[:len(z_norm)] * self.momentum + z_norm * (1.0 - self.momentum)
        lr = 0.01
        z = self._relu(x @ self.params['W1'] + self.params['b1'])
        z_j = self._relu(x_aug @ self.momentum_params['W1'] + self.momentum_params['b1'])
        batch_size = len(x)
        labels = np.zeros(batch_size, dtype=int)
        logits = z_i / (np.linalg.norm(z_i, axis=1, keepdims=True) + 1e-12)
        logits_q = z_j / (np.linalg.norm(z_j, axis=1, keepdims=True) + 1e-12)
        pos = np.sum(logits * logits_q, axis=1) / self.temperature
        queue_short = queue[:max(0, batch_size)] if len(queue) >= batch_size else queue
        neg = logits @ queue_short.T / self.temperature if len(queue_short) > 0 else np.zeros((batch_size, 1))
        if neg.shape[1] == 0:
            neg = np.zeros((batch_size, 1))
        logits = np.concatenate([pos[:, None], neg], axis=1)
        probs = self._softmax(logits)
        grad = probs.copy()
        grad[np.arange(batch_size), labels] -= 1
        grad /= batch_size
        dWp = z.T @ grad[:, :1]
        dbp = np.sum(grad[:, :1], axis=0)
        dh = grad[:, :1] @ self.params['Wp'].T
        dh = dh * (z > 0)
        dW1 = x.T @ dh
        db1 = np.sum(dh, axis=0)
        self.params["Wp"] -= lr * dWp
        self.params["bp"] -= lr * dbp
        self.params["W1"] -= lr * dW1
        self.params["b1"] -= lr * db1
        for k in self.momentum_params:
            self.momentum_params[k] = self.momentum * self.momentum_params[k] + (1.0 - self.momentum) * self.params[k]
        return {"loss": loss, "temperature": self.temperature, "queue_len": len(self.queue)}

    def mask_and_reconstruct(self, x: np.ndarray, mask_ratio: float = 0.15) -> Tuple[np.ndarray, np.ndarray]:
        mask = np.random.rand(*x.shape) < mask_ratio
        masked = x.copy()
        masked[mask] = 0.0
        target = x[mask]
        return masked, target

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
        return {"triplet_loss": loss}

    def get_ssl_report(self) -> Dict[str, Any]:
        return {
            "num_steps": len(self.loss_history),
            "last_loss": float(self.loss_history[-1]) if self.loss_history else None,
            "mean_loss": float(np.mean(self.loss_history[-10:])) if len(self.loss_history) >= 10 else (float(self.loss_history[-1]) if self.loss_history else None),
            "temperature": self.temperature,
            "queue_size": len(self.queue) if self.queue is not None else 0,
        }
