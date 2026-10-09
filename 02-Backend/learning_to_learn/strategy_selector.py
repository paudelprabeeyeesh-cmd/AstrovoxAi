from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Strategy:
    name: str
    complexity: float
    requirements: List[str] = field(default_factory=list)
    expected_performance: float = 0.5


class StrategySelector:
    def __init__(self):
        self.strategies: Dict[str, Strategy] = {}

    def register_strategy(self, strategy: Strategy) -> None:
        self.strategies[strategy.name] = strategy

    def select(self, task_features: Dict[str, float]) -> str:
        if not self.strategies:
            raise RuntimeError("No strategies registered")
        best_name = None
        best_score = float("-inf")
        for name, strategy in self.strategies.items():
            score = self._score_strategy(strategy, task_features)
            if score > best_score:
                best_score = score
                best_name = name
        return best_name or next(iter(self.strategies))

    def rank(self, task_features: Dict[str, float]) -> List[Tuple[str, float]]:
        scored = []
        for name, strategy in self.strategies.items():
            score = self._score_strategy(strategy, task_features)
            scored.append((name, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def _score_strategy(self, strategy: Strategy, task_features: Dict[str, float]) -> float:
        feature_count = len(task_features)
        complexity_penalty = strategy.complexity * 0.1
        feature_bonus = feature_count * 0.05
        base_score = strategy.expected_performance + feature_bonus - complexity_penalty
        for req in strategy.requirements:
            if req in task_features:
                base_score += 0.1
        return base_score

    def get_strategy(self, name: str) -> Optional[Strategy]:
        return self.strategies.get(name)
