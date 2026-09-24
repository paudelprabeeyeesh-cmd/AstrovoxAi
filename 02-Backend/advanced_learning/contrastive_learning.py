import numpy as np
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class SimCLRConfig:
    input_dim: int
    projection_dim: int = 128
    temperature: float = 0.07
    hidden_dim: int = 256


class SimCLR:
    def __init__(self, config: SimCLRConfig):
        self.config = config
        self.params: Dict[str, np.ndarray] = {}
        self.loss_history: List[float] = []
        self._initialize_params()

    def _initialize_params(self) -> None:
        d = self.config.input_dim
        h = self.config.hidden_dim
        p = self.config.projection_dim
        self.params['W1'] = np.random.randn(d, h).astype(np.float64) * np.sqrt(2.0 / d)
        self.params['b1'] = np.zeros(h, dtype=np.float64)
        self.params['W2'] = np.random.randn(h, p).astype(np.float64) * np.sqrt(2.0 / h)
        self.params['b2'] = np.zeros(p, dtype=np.float64)
        self.params['W3'] = np.random.randn(p, d).astype(np.float64) * np.sqrt(2.0 / p)
        self.params['b3'] = np.zeros(d, dtype=np.float64)

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

    def _project(self, x: np.ndarray) -> np.ndarray:
        h = self._relu(x @ self.params['W1'] + self.params['b1'])
        return h @ self.params['W2'] + self.params['b2']

    def _reconstruct(self, z: np.ndarray) -> np.ndarray:
        h = self._relu(z @ self.params['W3'] + self.params['b3'])
        return h @ self.params['W3'].T + self.params['b3']

    def _nt_xent_loss(self, z_i: np.ndarray, z_j: np.ndarray) -> float:
        N = len(z_i)
        z = np.concatenate([z_i, z_j], axis=0)
        z = z / (np.linalg.norm(z, axis=1, keepdims=True) + 1e-12)
        sim_matrix = z @ z.T
        mask = np.eye(2 * N, dtype=bool)
        sim_matrix = sim_matrix / self.config.temperature
        sim_matrix[mask] = -1e12
        labels = np.concatenate([np.arange(N) + N, np.arange(N)])
        logits = sim_matrix
        loss = float(-np.mean(np.log(self._softmax(logits)[np.arange(2 * N), labels] + 1e-12)))
        return loss

    def train_step(self, x_i: np.ndarray, x_j: np.ndarray) -> Dict[str, Any]:
        z_i = self._project(x_i)
        z_j = self._project(x_j)
        loss = self._nt_xent_loss(z_i, z_j)
        self.loss_history.append(loss)
        lr = 0.01
        z = np.concatenate([z_i, z_j], axis=0)
        z = z / (np.linalg.norm(z, axis=1, keepdims=True) + 1e-12)
        sim_matrix = z @ z.T / self.config.temperature
        mask = np.eye(2 * len(x_i), dtype=bool)
        sim_matrix[mask] = -1e12
        probs = self._softmax(sim_matrix)
        N = len(x_i)
        labels = np.concatenate([np.arange(N) + N, np.arange(N)])
        grad = probs.copy()
        grad[np.arange(2 * N), labels] -= 1
        grad /= (2 * N)
        h = self._relu(x_i @ self.params['W1'] + self.params['b1'])
        h_j = self._relu(x_j @ self.params['W1'] + self.params['b1'])
        np.concatenate([x_i, x_j], axis=0)
        h_all = np.concatenate([h, h_j], axis=0)
        dW3 = h_all.T @ grad @ np.concatenate([z_i, z_j], axis=0)
        db3 = np.sum(grad @ np.concatenate([z_i, z_j], axis=0).T, axis=0)
        dh = grad @ np.concatenate([z_i, z_j], axis=0).T @ self.params['W3'].T
        dz = dh[:N] + dh[N:]
        dW2 = h.T @ dz
        db2 = np.sum(dz, axis=0)
        dh2 = dz @ self.params['W2'].T * self._relu_grad(h)
        dW1 = x_i.T @ dh2
        db1 = np.sum(dh2, axis=0)
        self.params['W2'] -= lr * dW2
        self.params['b2'] -= lr * db2
        self.params['W1'] -= lr * dW1
        self.params['b1'] -= lr * db1
        self.params['W3'] -= lr * dW3[:len(h_all)]
        self.params['b3'] -= lr * db3[:len(h_all)]
        return {'loss': loss, 'temperature': self.config.temperature}

    def encode(self, x: np.ndarray) -> np.ndarray:
        return self._project(x)

    def evaluate(self, x: np.ndarray, x_pos: np.ndarray, x_neg: np.ndarray) -> Dict[str, float]:
        z = self.encode(x)
        z_pos = self.encode(x_pos)
        z_neg = self.encode(x_neg)
        pos = np.sum((z - z_pos) ** 2, axis=1)
        neg = np.sum((z[:, None, :] - z_neg[None, :, :]) ** 2, axis=2)
        margin = 0.2
        loss = float(np.mean(np.maximum(margin + pos[:, None] - neg, 0)))
        return {'triplet_loss': loss}

    def get_report(self) -> Dict[str, Any]:
        return {
            'num_steps': len(self.loss_history),
            'last_loss': float(self.loss_history[-1]) if self.loss_history else None,
            'mean_loss': float(np.mean(self.loss_history[-10:])) if len(self.loss_history) >= 10 else (float(self.loss_history[-1]) if self.loss_history else None),
            'temperature': self.config.temperature,
            'projection_dim': self.config.projection_dim,
        }
