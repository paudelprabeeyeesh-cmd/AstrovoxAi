import numpy as np
from typing import Dict, List, Optional, Any, Tuple


class SelfSupervisedLearner:
    def __init__(self, temperature: float = 0.1, projection_dim: int = 128):
        self.temperature = temperature
        self.projection_dim = projection_dim
        self.projection_matrix: Optional[np.ndarray] = None
        self.loss_history: List[float] = []

    def _project(self, x: np.ndarray) -> np.ndarray:
        if self.projection_matrix is None:
            self.projection_matrix = np.random.randn(x.shape[1], self.projection_dim).astype(np.float64) * 0.1
        return x @ self.projection_matrix

    def nt_xent_loss(self, z_i: np.ndarray, z_j: np.ndarray) -> float:
        z_i = self._project(z_i)
        z_j = self._project(z_j)
        z = np.concatenate([z_i, z_j], axis=0)
        sim_matrix = self._cosine_similarity(z, z)
        N = len(z_i)
        labels = np.arange(N)
        labels = np.concatenate([labels + N, labels])
        logits = sim_matrix / self.temperature
        loss = -np.mean(np.log(np.exp(logits[np.arange(2 * N), labels]) / (np.sum(np.exp(logits), axis=1) + 1e-12) + 1e-12))
        self.loss_history.append(float(loss))
        return float(loss)

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        a_norm = np.linalg.norm(a, axis=1, keepdims=True) + 1e-12
        b_norm = np.linalg.norm(b, axis=1, keepdims=True) + 1e-12
        return (a @ b.T) / (a_norm @ b_norm.T)

    def mask_and_reconstruct(self, x: np.ndarray, mask_ratio: float = 0.3) -> Tuple[np.ndarray, np.ndarray]:
        B, D = x.shape
        num_masked = max(1, int(D * mask_ratio))
        mask = np.random.permutation(D)[:num_masked]
        x_masked = np.array(x)
        x_masked[:, mask] = 0.0
        target = x[:, mask]
        return x_masked, target

    def train_step(self, x: np.ndarray, y: Optional[np.ndarray] = None) -> Dict[str, float]:
        x1 = x + np.random.randn(*x.shape).astype(np.float64) * 0.01
        x2 = x + np.random.randn(*x.shape).astype(np.float64) * 0.01
        loss = self.nt_xent_loss(x1, x2)
        return {"contrastive_loss": loss}

    def get_ssl_report(self) -> Dict[str, Any]:
        return {
            "num_steps": len(self.loss_history),
            "last_loss": self.loss_history[-1] if self.loss_history else None,
            "temperature": self.temperature,
            "projection_dim": self.projection_dim,
        }
