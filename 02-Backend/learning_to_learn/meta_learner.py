from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Task:
    task_id: str
    features: Dict[str, float]
    metadata: Dict[str, Any] = field(default_factory=dict)
    performance_history: List[float] = field(default_factory=list)


@dataclass
class MetaParameters:
    learning_rate: float = 0.01
    momentum: float = 0.9
    exploration_rate: float = 0.1
    task_similarity_threshold: float = 0.7
    adaptation_memory: Dict[str, float] = field(default_factory=dict)


class MetaLearner:
    def __init__(self, meta_params: Optional[MetaParameters] = None):
        self.meta_params = meta_params or MetaParameters()
        self.tasks: Dict[str, Task] = {}
        self.strategy_selector: Optional["StrategySelector"] = None
        self.transfer_prior: Optional["TransferPrior"] = None
        self.adaptation_tracker: Optional["AdaptationTracker"] = None

    def register_task(self, task: Task) -> None:
        self.tasks[task.task_id] = task

    def update_performance(self, task_id: str, performance: float) -> None:
        if task_id not in self.tasks:
            raise KeyError(f"Task {task_id} not registered")
        self.tasks[task_id].performance_history.append(performance)
        if self.adaptation_tracker is not None:
            self.adaptation_tracker.record_step(task_id, performance)

    def set_components(
        self,
        strategy_selector: Optional["StrategySelector"] = None,
        transfer_prior: Optional["TransferPrior"] = None,
        adaptation_tracker: Optional["AdaptationTracker"] = None,
    ) -> None:
        if strategy_selector is not None:
            self.strategy_selector = strategy_selector
        if transfer_prior is not None:
            self.transfer_prior = transfer_prior
        if adaptation_tracker is not None:
            self.adaptation_tracker = adaptation_tracker

    def meta_update(self) -> MetaParameters:
        performances: List[float] = []
        for task in self.tasks.values():
            if task.performance_history:
                performances.append(task.performance_history[-1])

        if performances:
            avg_performance = sum(performances) / len(performances)
            self.meta_params.adaptation_memory["avg_performance"] = avg_performance
            if avg_performance < 0.5:
                self.meta_params.exploration_rate = min(
                    self.meta_params.exploration_rate * 1.1, 0.5
                )
            else:
                self.meta_params.exploration_rate = max(
                    self.meta_params.exploration_rate * 0.95, 0.01
                )

        return self.meta_params

    def predict_best_strategy(self, task_id: str) -> str:
        if self.strategy_selector is None:
            raise RuntimeError("StrategySelector not attached")
        if task_id not in self.tasks:
            raise KeyError(f"Task {task_id} not registered")
        return self.strategy_selector.select(self.tasks[task_id].features)

    def suggest_prior(self, target_task_id: str) -> Optional[Dict[str, float]]:
        if self.transfer_prior is None:
            return None
        if target_task_id not in self.tasks:
            return None
        return self.transfer_prior.suggest(self.tasks[target_task_id].features)

    def get_task_stats(self, task_id: str) -> Dict[str, Any]:
        if task_id not in self.tasks:
            raise KeyError(f"Task {task_id} not registered")
        task = self.tasks[task_id]
        history = task.performance_history
        if not history:
            return {"task_id": task_id, "avg_performance": 0.0, "num_updates": 0}
        return {
            "task_id": task_id,
            "avg_performance": sum(history) / len(history),
            "num_updates": len(history),
            "latest_performance": history[-1],
        }
