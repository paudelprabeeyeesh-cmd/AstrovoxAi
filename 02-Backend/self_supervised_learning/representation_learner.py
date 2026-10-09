import math
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .contrastive_loss import nt_xent_loss
from .masked_modeling import mask_float_vector, reconstruction_loss
from .augmentation_pipeline import AugmentationPipeline, GaussianNoise, Dropout

Vector = List[float]


@dataclass
class RepresentationLearnerConfig:
    projection_dim: int = 128
    temperature: float = 0.1
    mask_ratio: float = 0.3


class RepresentationLearner:
    def __init__(self, config: Optional[RepresentationLearnerConfig] = None):
        self.config = config or RepresentationLearnerConfig()
        self.projection: Optional[List[List[float]]] = None
        self.loss_history: List[float] = []
        self.pipeline = AugmentationPipeline(transforms=[GaussianNoise(std=0.01), Dropout(p=0.1)])

    def _ensure_projection(self, dim: int) -> None:
        if self.projection is None:
            proj_dim = self.config.projection_dim
            scale = math.sqrt(2.0 / (dim + proj_dim))
            self.projection = [[random.gauss(0.0, scale) for _ in range(proj_dim)] for _ in range(dim)]

    def _project(self, x: Vector) -> Vector:
        dim = len(x)
        self._ensure_projection(dim)
        result = [0.0] * self.config.projection_dim
        for j in range(self.config.projection_dim):
            s = 0.0
            for i in range(dim):
                s += x[i] * self.projection[i][j]
            result[j] = s
        return result

    def train_step(self, x: List[Vector]) -> Dict[str, Any]:
        x1 = [self.pipeline(v) for v in x]
        x2 = [self.pipeline(v) for v in x]
        z1 = [self._project(v) for v in x1]
        z2 = [self._project(v) for v in x2]
        loss = nt_xent_loss(z1, z2, temperature=self.config.temperature)
        self.loss_history.append(loss)
        return {"contrastive_loss": loss}

    def encode(self, x: Vector) -> Vector:
        return self._project(x)

    def masked_reconstruction_step(self, x: List[Vector]) -> Dict[str, Any]:
        results = [mask_float_vector(v, self.config.mask_ratio) for v in x]
        masked = [r[0] for r in results]
        targets = [r[1] for r in results]
        indices = [r[2] for r in results]
        rec_losses = [reconstruction_loss(orig, mask_vec, idxs) for orig, mask_vec, idxs in zip(x, masked, indices)]
        avg_rec = sum(rec_losses) / len(rec_losses) if rec_losses else 0.0
        return {"reconstruction_loss": avg_rec}

    def report(self) -> Dict[str, Any]:
        return {
            "num_steps": len(self.loss_history),
            "last_loss": self.loss_history[-1] if self.loss_history else None,
            "config": {
                "temperature": self.config.temperature,
                "projection_dim": self.config.projection_dim,
                "mask_ratio": self.config.mask_ratio,
            },
        }
