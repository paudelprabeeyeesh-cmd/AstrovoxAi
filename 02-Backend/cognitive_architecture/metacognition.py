from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import time


@dataclass
class MetacognitiveEvent:
    event_type: str
    confidence: float
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class MetacognitiveMonitor:
    def __init__(self, confidence_threshold: float = 0.7):
        self.confidence_threshold = confidence_threshold
        self.events: List[MetacognitiveEvent] = []
        self.accuracy_history: List[float] = []
        self._current_confidence: float = 1.0

    def evaluate_confidence(self, estimate: float, uncertainty: float) -> float:
        confidence = max(0.0, min(1.0, 1.0 - uncertainty))
        self._current_confidence = confidence
        self.events.append(MetacognitiveEvent(
            event_type="confidence_evaluation",
            confidence=confidence,
            timestamp=time.time(),
            metadata={"estimate": estimate, "uncertainty": uncertainty},
        ))
        return confidence

    def record_outcome(self, predicted_confidence: float, actual_correct: bool) -> None:
        accuracy = 1.0 if actual_correct else 0.0
        self.accuracy_history.append(accuracy)
        self.events.append(MetacognitiveEvent(
            event_type="outcome",
            confidence=predicted_confidence,
            timestamp=time.time(),
            metadata={"correct": actual_correct},
        ))

    def get_calibration_error(self) -> float:
        outcome_events = [e for e in self.events if e.event_type == "outcome"]
        if len(outcome_events) < 2 or len(self.accuracy_history) < 2:
            return 0.0
        errors = [abs(e.confidence - a) for e, a in zip(outcome_events[:len(self.accuracy_history)], self.accuracy_history)]
        return sum(errors) / len(errors)

    def should_request_help(self) -> bool:
        return self._current_confidence < self.confidence_threshold

    def get_metacognitive_state(self) -> Dict[str, Any]:
        return {
            "current_confidence": self._current_confidence,
            "threshold": self.confidence_threshold,
            "events_count": len(self.events),
            "accuracy": sum(self.accuracy_history) / len(self.accuracy_history) if self.accuracy_history else 0.0,
            "needs_help": self.should_request_help(),
        }


class LearningAboutLearning:
    def __init__(self):
        self.strategy_performance: Dict[str, List[float]] = {}
        self.task_difficulty_estimates: Dict[str, float] = {}

    def record_strategy_result(self, strategy: str, success: bool) -> None:
        if strategy not in self.strategy_performance:
            self.strategy_performance[strategy] = []
        self.strategy_performance[strategy].append(1.0 if success else 0.0)

    def get_best_strategy(self) -> Optional[str]:
        best_strategy = None
        best_score = -1.0
        for strategy, results in self.strategy_performance.items():
            score = sum(results) / len(results)
            if score > best_score:
                best_score = score
                best_strategy = strategy
        return best_strategy

    def estimate_task_difficulty(self, task_id: str, features: Dict[str, float]) -> float:
        difficulty = sum(features.values()) / len(features) if features else 0.5
        self.task_difficulty_estimates[task_id] = difficulty
        return difficulty
