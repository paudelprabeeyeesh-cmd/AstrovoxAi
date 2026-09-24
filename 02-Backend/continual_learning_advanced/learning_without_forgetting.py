from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class LwFConfig:
    alpha: float = 1.0
    temperature: float = 2.0


class LearningWithoutForgetting:
    def __init__(self, config: Optional[LwFConfig] = None):
        self.config = config or LwFConfig()
        self.old_model_params: Dict[str, List[float]] = {}
        self.task_outputs: Dict[int, List[List[float]]] = {}
        self.task_loss_history: Dict[int, List[float]] = {}

    def freeze_old_model(self, params: Dict[str, List[float]]) -> None:
        self.old_model_params = {k: list(v) for k, v in params.items()}

    def _softmax(self, logits: List[float]) -> List[float]:
        max_logit = max(logits) if logits else 0.0
        exps = [math.exp(x - max_logit) for x in logits]
        total = sum(exps)
        return [e / total for e in exps] if total > 0 else [0.0] * len(logits)

    def _forward_logits(self, params: Dict[str, List[float]], x: List[float]) -> List[float]:
        W = params.get('W', [])
        b = params.get('b', [])
        if not W:
            return [0.0] * len(b)
        out_dim = len(b)
        in_dim = len(x)
        logits: List[float] = []
        for j in range(out_dim):
            s = 0.0
            for i in range(in_dim):
                s += W[j * in_dim + i] * x[i]
            s += b[j]
            logits.append(s)
        return logits

    def distillation_loss(self, current_params: Dict[str, List[float]], x: List[float]) -> float:
        if not self.old_model_params:
            return 0.0
        old_logits = self._forward_logits(self.old_model_params, x)
        new_logits = self._forward_logits(current_params, x)
        old_probs = self._softmax([v / self.config.temperature for v in old_logits])
        new_probs = self._softmax([v / self.config.temperature for v in new_logits])
        loss = 0.0
        for p, q in zip(old_probs, new_probs):
            if p > 0:
                loss -= p * math.log(q + 1e-9)
        return loss * (self.config.temperature ** 2)

    def train_step_loss(
        self,
        task_id: int,
        current_params: Dict[str, List[float]],
        x: List[float],
        y: List[float],
    ) -> float:
        logits = self._forward_logits(current_params, x)
        task_loss = sum((logits[i] - y[i]) ** 2 for i in range(len(y))) / len(y)
        dist_loss = self.distillation_loss(current_params, x)
        total = task_loss + self.config.alpha * dist_loss
        self.task_loss_history.setdefault(task_id, []).append(total)
        return total

    def register_task_outputs(self, task_id: int, outputs: List[List[float]]) -> None:
        self.task_outputs[task_id] = [list(row) for row in outputs]

    def get_task_report(self, task_id: int) -> Dict[str, float]:
        losses = self.task_loss_history.get(task_id, [])
        if not losses:
            return {"task_id": float(task_id), "avg_loss": 0.0, "steps": 0}
        return {
            "task_id": float(task_id),
            "avg_loss": sum(losses) / len(losses),
            "steps": float(len(losses)),
        }
