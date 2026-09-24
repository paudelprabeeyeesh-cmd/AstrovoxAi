import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class CurriculumConfig:
    input_dim: int
    output_dim: int
    hidden_dim: int = 64
    pacing_type: str = "linear"
    pacing_start_frac: float = 0.1
    pacing_epochs: int = 10
    difficulty_metric: str = "loss"


class AdvancedCurriculumLearner:
    def __init__(self, config: CurriculumConfig):
        self.config = config
        self.params: Dict[str, np.ndarray] = {}
        self.loss_history: List[float] = []
        self.difficulty_scores: List[float] = []
        self.sample_mask: Optional[np.ndarray] = None
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

    def _compute_difficulty(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        if self.config.difficulty_metric == "loss":
            logits = self._forward(x, self.params)
            return np.mean((logits - y) ** 2, axis=1)
        elif self.config.difficulty_metric == "gradient_norm":
            logits = self._forward(x, self.params)
            np.mean((logits - y) ** 2)
            grad = 2.0 * (logits - y) / x.shape[0]
            h = self._relu(x @ self.params['W1'] + self.params['b1'])
            dh = grad @ self.params['W2'].T * self._relu_grad(h)
            dw1 = x.T @ dh
            dw1_per_sample = x[:, :, None] * dh[:, None, :]
            return np.linalg.norm(dw1_per_sample, axis=(1, 2))
        else:
            return np.random.rand(len(x)).astype(np.float64)

    def _compute_pacing(self, epoch: int) -> float:
        t = self.config.pacing_epochs
        start = self.config.pacing_start_frac
        if self.config.pacing_type == "linear":
            return min(1.0, start + (1.0 - start) * epoch / t)
        elif self.config.pacing_type == "exponential":
            return min(1.0, start * (1.0 - start) ** (epoch / t))
        else:
            return min(1.0, start + (1.0 - start) * epoch / t)

    def score_difficulty(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        scores = self._compute_difficulty(x, y)
        self.difficulty_scores.extend(scores.tolist())
        return scores

    def update_mask(self, x: np.ndarray, epoch: int) -> np.ndarray:
        scores = self.score_difficulty(x, np.zeros((len(x), self.config.output_dim)))
        sorted_idx = np.argsort(scores)
        frac = self._compute_pacing(epoch)
        n = max(1, int(len(x) * frac))
        mask = np.zeros(len(x), dtype=bool)
        mask[sorted_idx[:n]] = True
        self.sample_mask = mask
        return mask

    def train_step(self, x: np.ndarray, y: np.ndarray, epoch: int = 0, lr: float = 0.01) -> Dict[str, Any]:
        if self.sample_mask is None or len(self.sample_mask) != len(x):
            self.update_mask(x, epoch)
        mask = self.sample_mask
        x_sel = x[mask]
        y_sel = y[mask]
        logits = self._forward(x_sel, self.params)
        loss = float(np.mean((logits - y_sel) ** 2))
        self.loss_history.append(loss)
        grad = 2.0 * (logits - y_sel) / x_sel.shape[0]
        h = self._relu(x_sel @ self.params['W1'] + self.params['b1'])
        db2 = np.sum(grad, axis=0)
        dw2 = h.T @ grad
        dh = grad @ self.params['W2'].T * self._relu_grad(h)
        db1 = np.sum(dh, axis=0)
        dw1 = x_sel.T @ dh
        self.params['W2'] -= lr * dw2
        self.params['b2'] -= lr * db2
        self.params['W1'] -= lr * dw1
        self.params['b1'] -= lr * db1
        return {'loss': loss, 'epoch': epoch, 'samples_used': int(np.sum(mask)), 'pacing_frac': self._compute_pacing(epoch)}

    def get_curriculum_report(self) -> Dict[str, Any]:
        return {
            'num_steps': len(self.loss_history),
            'last_loss': float(self.loss_history[-1]) if self.loss_history else None,
            'mean_loss': float(np.mean(self.loss_history[-10:])) if len(self.loss_history) >= 10 else (float(self.loss_history[-1]) if self.loss_history else None),
            'pacing_type': self.config.pacing_type,
            'pacing_start_frac': self.config.pacing_start_frac,
            'difficulty_metric': self.config.difficulty_metric,
            'num_scored_samples': len(self.difficulty_scores),
        }
