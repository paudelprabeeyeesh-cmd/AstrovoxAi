"""Meta-learning and MAML-style adaptation examples."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TaskBatch:
    support_x: list[Any]
    support_y: list[Any]
    query_x: list[Any]
    query_y: list[Any]
    metadata: dict[str, Any] = field(default_factory=dict)


class MAMLStep:
    def __init__(self, inner_lr: float = 0.01, inner_steps: int = 5):
        self.inner_lr = inner_lr
        self.inner_steps = inner_steps

    def adapt(self, model: Any, task: TaskBatch) -> Any:
        adapted = self._clone_model(model)
        for _ in range(self.inner_steps):
            loss = self._compute_loss(adapted, task.support_x, task.support_y)
            self._update_params(adapted, loss)
        return adapted

    def meta_update(self, model: Any, adapted_models: list[Any], tasks: list[TaskBatch]) -> tuple[Any, float]:
        meta_loss = 0.0
        for adapted, task in zip(adapted_models, tasks):
            loss = self._compute_loss(adapted, task.query_x, task.query_y)
            meta_loss += loss
        meta_loss /= max(len(adapted_models), 1)
        self._update_params(model, meta_loss)
        return model, meta_loss

    def _clone_model(self, model: Any) -> Any:
        try:
            import copy
            return copy.deepcopy(model)
        except Exception:
            return model

    def _compute_loss(self, model: Any, x: list[Any], y: list[Any]) -> float:
        if not x or not y:
            return 0.0
        total = 0.0
        for xi, yi in zip(x, y):
            pred = float(model(xi) if callable(getattr(model, "__call__", None)) else 0.0)
            total += (pred - float(yi)) ** 2
        return total / max(len(x), 1)

    def _update_params(self, model: Any, loss: float) -> None:
        if hasattr(model, "parameters"):
            for param in model.parameters():
                if hasattr(param, "grad"):
                    param -= self.inner_lr * (param.grad or 0.0)
        if hasattr(model, "zero_grad"):
            try:
                model.zero_grad()
            except Exception:
                pass


class ReptileStep:
    def __init__(self, inner_lr: float = 0.01, inner_steps: int = 10, meta_lr: float = 0.1):
        self.inner_lr = inner_lr
        self.inner_steps = inner_steps
        self.meta_lr = meta_lr

    def adapt(self, model: Any, task: TaskBatch) -> Any:
        maml = MAMLStep(inner_lr=self.inner_lr, inner_steps=self.inner_steps)
        return maml.adapt(model, task)

    def meta_update(self, model: Any, adapted_models: list[Any]) -> Any:
        if not adapted_models:
            return model
        total = self._zero_like(model)
        for adapted in adapted_models:
            diff = self._param_diff(adapted, model)
            total = self._add_params(total, diff)
        avg = self._scale_params(total, 1.0 / len(adapted_models))
        updated = self._interpolate_params(model, avg, self.meta_lr)
        return updated

    def _zero_like(self, model: Any) -> Any:
        return model

    def _param_diff(self, a: Any, b: Any) -> Any:
        return a

    def _add_params(self, a: Any, b: Any) -> Any:
        return a

    def _scale_params(self, params: Any, scale: float) -> Any:
        return params

    def _interpolate_params(self, base: Any, delta: Any, lr: float) -> Any:
        return base


class FOMAMLStep:
    def __init__(self, inner_lr: float = 0.01, inner_steps: int = 1):
        self.inner_lr = inner_lr
        self.inner_steps = inner_steps
        self.maml = MAMLStep(inner_lr=inner_lr, inner_steps=inner_steps)

    def adapt(self, model: Any, task: TaskBatch) -> Any:
        return self.maml.adapt(model, task)

    def meta_update(self, model: Any, adapted_models: list[Any], tasks: list[TaskBatch]) -> tuple[Any, float]:
        return self.maml.meta_update(model, adapted_models, tasks)
