import numpy as np
from typing import Dict, Any, List, Optional

from .projection_head import ProjectionHead
from .temperature_scheduler import TemperatureScheduler
from .triplet_miner import TripletMiner


class SimCLRWrapper:
    def __init__(
        self,
        input_dim: int,
        projection_dim: int = 128,
        hidden_dim: int = 256,
        temperature: float = 0.07,
        seed: Optional[int] = None,
    ):
        self.input_dim = input_dim
        self.projection_dim = projection_dim
        self.hidden_dim = hidden_dim
        self.config_temperature = float(temperature)

        self.projection_head = ProjectionHead(
            input_dim=input_dim,
            hidden_dim=hidden_dim,
            output_dim=projection_dim,
            seed=seed,
        )
        self.temperature_scheduler = TemperatureScheduler(
            initial_temperature=temperature,
            schedule="constant",
        )
        self.triplet_miner = TripletMiner(margin=0.2)
        self.loss_history: List[float] = []

    @staticmethod
    def _normalize(x: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(x, axis=1, keepdims=True) + 1e-12
        return x / norms

    def _nt_xent_loss(self, z_i: np.ndarray, z_j: np.ndarray) -> float:
        N = len(z_i)
        z = np.concatenate([z_i, z_j], axis=0)
        z = self._normalize(z)
        sim_matrix = z @ z.T
        temp = self.temperature_scheduler.get()
        sim_matrix = sim_matrix / temp
        mask = np.eye(2 * N, dtype=bool)
        sim_matrix[mask] = -1e12
        labels = np.concatenate([np.arange(N) + N, np.arange(N)])

        logits = sim_matrix
        max_logits = np.max(logits, axis=1, keepdims=True)
        exp_logits = np.exp(logits - max_logits)
        log_probs = (logits - max_logits) - np.log(np.sum(exp_logits, axis=1, keepdims=True) + 1e-12)
        loss = float(-np.mean(log_probs[np.arange(2 * N), labels]))
        return loss

    def train_step(self, x_i: np.ndarray, x_j: np.ndarray, labels: Optional[np.ndarray] = None) -> Dict[str, Any]:
        if x_i.shape[1] != self.input_dim or x_j.shape[1] != self.input_dim:
            raise ValueError("Input dimensions do not match model input_dim")

        z_i = self.projection_head.forward(x_i)
        z_j = self.projection_head.forward(x_j)
        loss = self._nt_xent_loss(z_i, z_j)
        self.loss_history.append(loss)

        self.temperature_scheduler.step()

        result: Dict[str, Any] = {
            "loss": loss,
            "temperature": self.temperature_scheduler.get(),
        }

        if labels is not None:
            embeddings = np.concatenate([x_i, x_j], axis=0)
            all_labels = np.concatenate([labels, labels], axis=0)
            mined = self.triplet_miner.mine(embeddings, all_labels, strategy="random", num_triplets=min(32, len(embeddings)))
            triplet_loss = self.triplet_miner.compute_triplet_loss(embeddings, mined["anchors"], mined["positives"], mined["negatives"])
            result["triplet_loss"] = triplet_loss

        return result

    def encode(self, x: np.ndarray) -> np.ndarray:
        if x.shape[1] != self.input_dim:
            raise ValueError("Input dimensions do not match model input_dim")
        return self.projection_head.forward(x)

    def evaluate(self, x: np.ndarray, x_pos: np.ndarray, x_neg: np.ndarray) -> Dict[str, float]:
        z = self.encode(x)
        z_pos = self.encode(x_pos)
        z_neg = self.encode(x_neg)

        pos = np.sum((z - z_pos) ** 2, axis=1)
        neg = np.sum((z[:, None, :] - z_neg[None, :, :]) ** 2, axis=2)
        loss = float(np.mean(np.maximum(self.triplet_miner.margin + pos[:, None] - neg, 0)))
        return {"triplet_loss": loss}

    def get_report(self) -> Dict[str, Any]:
        return {
            "num_steps": len(self.loss_history),
            "last_loss": float(self.loss_history[-1]) if self.loss_history else None,
            "mean_loss": float(np.mean(self.loss_history[-10:])) if len(self.loss_history) >= 10 else (float(self.loss_history[-1]) if self.loss_history else None),
            "temperature": self.temperature_scheduler.get(),
            "projection_dim": self.projection_dim,
        }
