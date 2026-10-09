from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class FineTuneTask:
    task_id: str
    epochs: int
    learning_rate: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FineTuneResult:
    task_id: str
    final_loss: float
    steps: int
    metrics: Dict[str, Any] = field(default_factory=dict)


class FineTuningManager:
    def __init__(
        self,
        model: Any,
        loss_fn: Optional[Callable[[Any, Any], float]] = None,
    ) -> None:
        self.model = model
        self.loss_fn = loss_fn or self._default_loss
        self.task_registry: Dict[str, FineTuneTask] = {}
        self.results: Dict[str, FineTuneResult] = {}
        self.history: Dict[str, List[float]] = {}

    @staticmethod
    def _default_loss(predictions: Any, targets: Any) -> float:
        if isinstance(predictions, list) and isinstance(targets, list):
            correct = sum(1 for p, t in zip(predictions, targets) if p == t)
            return 1.0 - (correct / max(len(targets), 1))
        if isinstance(predictions, (int, float)) and isinstance(targets, (int, float)):
            return abs(float(predictions) - float(targets))
        return 0.0

    def register_task(
        self,
        task_id: str,
        epochs: int = 1,
        learning_rate: float = 0.01,
        **metadata: Any,
    ) -> None:
        if task_id in self.task_registry:
            raise ValueError(f"Task '{task_id}' is already registered")
        self.task_registry[task_id] = FineTuneTask(
            task_id=task_id,
            epochs=max(1, epochs),
            learning_rate=learning_rate,
            metadata=metadata,
        )

    def _apply_learning_rate(self, base_lr: float, epoch: int, total_epochs: int) -> float:
        decay = 1.0 - (epoch / max(total_epochs, 1))
        return base_lr * max(decay, 0.01)

    def run(
        self,
        task_id: str,
        data: List[Tuple[Any, Any]],
        on_step: Optional[Callable[[int, float], None]] = None,
    ) -> FineTuneResult:
        if task_id not in self.task_registry:
            raise KeyError(f"Task '{task_id}' is not registered")
        task = self.task_registry[task_id]
        losses: List[float] = []
        step = 0
        for epoch in range(task.epochs):
            lr = self._apply_learning_rate(task.learning_rate, epoch, task.epochs)
            for x, y in data:
                loss = self.loss_fn(self.model(x) if callable(getattr(self.model, "__call__", None)) else x, y)
                losses.append(loss)
                step += 1
                if on_step is not None:
                    on_step(step, loss)
        self.history[task_id] = losses
        result = FineTuneResult(
            task_id=task_id,
            final_loss=losses[-1] if losses else 0.0,
            steps=step,
            metrics={"mean_loss": sum(losses) / max(len(losses), 1), "min_loss": min(losses) if losses else 0.0},
        )
        self.results[task_id] = result
        return result

    def run_all(
        self,
        data_map: Dict[str, List[Tuple[Any, Any]]],
        on_step: Optional[Callable[[str, int, float], None]] = None,
    ) -> Dict[str, FineTuneResult]:
        results: Dict[str, FineTuneResult] = {}
        for task_id, data in data_map.items():
            def _on_step(step: int, loss: float, tid: str = task_id) -> None:
                if on_step is not None:
                    on_step(tid, step, loss)
            results[task_id] = self.run(task_id, data, on_step=_on_step)
        return results

    def get_history(self, task_id: str) -> List[float]:
        if task_id not in self.history:
            raise KeyError(f"No history for task '{task_id}'")
        return list(self.history[task_id])

    def summary(self) -> Dict[str, Any]:
        return {
            "registered_tasks": list(self.task_registry.keys()),
            "completed_tasks": list(self.results.keys()),
            "task_losses": {tid: r.final_loss for tid, r in self.results.items()},
        }
