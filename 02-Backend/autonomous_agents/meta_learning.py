from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import numpy as np


@dataclass
class Task:
    id: str
    domain: str
    features: np.ndarray
    label: Optional[float] = None


@dataclass
class MetaStrategy:
    name: str
    weights: np.ndarray
    performance_history: List[float] = field(default_factory=list)


class MetaLearning:
    def __init__(self, feature_dim: int = 8, num_strategies: int = 4):
        self.feature_dim = feature_dim
        self.num_strategies = num_strategies
        self.strategies: Dict[str, MetaStrategy] = {}
        self.task_buffer: List[Task] = []
        self.buffer_size = 200
        self._counter = 0
        for i in range(num_strategies):
            name = f"strategy_{i}"
            self.strategies[name] = MetaStrategy(
                name=name,
                weights=np.random.randn(feature_dim) * 0.1,
            )

    def add_task(self, domain: str, features: np.ndarray, label: Optional[float] = None) -> Task:
        self._counter += 1
        task = Task(id=f"task_{self._counter}", domain=domain, features=np.array(features, dtype=np.float64), label=label)
        self.task_buffer.append(task)
        if len(self.task_buffer) > self.buffer_size:
            self.task_buffer.pop(0)
        return task

    def select_strategy(self, task_features: np.ndarray) -> MetaStrategy:
        scores = {}
        for name, strat in self.strategies.items():
            score = float(np.dot(strat.weights, task_features))
            if strat.performance_history:
                score += 0.5 * np.mean(strat.performance_history[-5:])
            scores[name] = score
        best_name = max(scores, key=scores.get)
        return self.strategies[best_name]

    def adapt_strategy(self, strategy_name: str, task_features: np.ndarray, reward: float, lr: float = 0.05) -> None:
        strat = self.strategies.get(strategy_name)
        if strat is None:
            return
        grad = task_features * (1.0 - reward)
        strat.weights = strat.weights + lr * grad
        norm = np.linalg.norm(strat.weights)
        if norm > 1.0:
            strat.weights = strat.weights / norm
        strat.performance_history.append(max(0.0, min(1.0, reward)))
        if len(strat.performance_history) > 100:
            strat.performance_history.pop(0)

    def rapid_adapt(self, new_task: Task, episodes: int = 5) -> Dict[str, Any]:
        strategy = self.select_strategy(new_task.features)
        rewards = []
        for _ in range(episodes):
            reward = self._simulate_performance(strategy, new_task)
            self.adapt_strategy(strategy.name, new_task.features, reward)
            rewards.append(reward)
        return {
            "strategy": strategy.name,
            "rewards": rewards,
            "final_reward": rewards[-1] if rewards else 0.0,
            "improvement": rewards[-1] - rewards[0] if len(rewards) > 1 else 0.0,
            "episodes": episodes,
        }

    def _simulate_performance(self, strategy: MetaStrategy, task: Task) -> float:
        logits = np.dot(strategy.weights, task.features)
        prob = 1.0 / (1.0 + np.exp(-logits))
        noise = np.random.normal(0, 0.05)
        return max(0.0, min(1.0, prob + noise))

    def get_strategy_performance(self) -> Dict[str, float]:
        return {
            name: float(np.mean(strat.performance_history)) if strat.performance_history else 0.0
            for name, strat in self.strategies.items()
        }
