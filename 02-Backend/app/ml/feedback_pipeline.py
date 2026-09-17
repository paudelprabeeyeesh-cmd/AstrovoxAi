import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class FeedbackReport:
    model_id: str
    feedback_count: int
    average_score: float
    issues: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TrainingData:
    model_id: str
    samples: list[dict[str, Any]] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.utcnow)


class FeedbackPipeline:
    def __init__(self, model_registry: Any) -> None:
        self.model_registry = model_registry
        self._feedback: dict[str, list[dict[str, Any]]] = {}

    def collect_feedback(self, response_id: str, feedback: dict[str, Any]) -> None:
        self._feedback.setdefault(response_id, []).append(feedback)
        logger.info(f"Collected feedback for response {response_id}")

    def aggregate_feedback(self, model_id: str) -> FeedbackReport:
        feedback_items: list[dict[str, Any]] = []
        for items in self._feedback.values():
            for item in items:
                if item.get("model_id") == model_id:
                    feedback_items.append(item)

        scores = [item.get("score", 0.0) for item in feedback_items if isinstance(item.get("score"), (int, float))]
        average_score = sum(scores) / len(scores) if scores else 0.0
        issues = [item.get("issue", "") for item in feedback_items if item.get("issue")]

        return FeedbackReport(model_id=model_id, feedback_count=len(feedback_items), average_score=average_score, issues=issues)

    def generate_training_data(self, model_id: str, min_feedback_count: int) -> TrainingData:
        report = self.aggregate_feedback(model_id)
        if report.feedback_count < min_feedback_count:
            logger.warning(f"Insufficient feedback for model {model_id}: {report.feedback_count} < {min_feedback_count}")
        samples: list[dict[str, Any]] = []
        for items in self._feedback.values():
            for item in items:
                if item.get("model_id") == model_id:
                    samples.append(item)
        return TrainingData(model_id=model_id, samples=samples)
