"""Learning engine: collects feedback, failures, and quality signals and
emits improvement reports.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from . import make_id, now
from ..logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class FeedbackEvent:
    id: str
    category: str
    rating: float  # -1.0 .. 1.0
    comment: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "rating": round(self.rating, 4),
            "comment": self.comment,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


class LearningEngine:
    """Aggregates feedback and produces improvement reports."""

    def __init__(self) -> None:
        self._feedback: List[FeedbackEvent] = []
        self._failures: List[Dict[str, Any]] = []
        self._latencies: List[float] = []
        self._hallucinations: List[Dict[str, Any]] = []
        self._retrieval_qualities: List[float] = []
        self._planner_qualities: List[float] = []
        self._tool_successes: List[bool] = []
        self._workflow_successes: List[bool] = []

    # ---- recording --------------------------------------------------

    def record_feedback(
        self,
        category: str,
        rating: float,
        comment: str = "",
        **metadata: Any,
    ) -> FeedbackEvent:
        event = FeedbackEvent(
            id=make_id("fb"),
            category=category,
            rating=max(-1.0, min(1.0, rating)),
            comment=comment,
            metadata=dict(metadata),
        )
        self._feedback.append(event)
        return event

    def record_failure(self, target: str, *, error: str, severity: str = "warning") -> None:
        self._failures.append(
            {"target": target, "error": error, "severity": severity, "ts": now()}
        )

    def record_latency(self, ms: float) -> None:
        self._latencies.append(ms)

    def record_hallucination(self, target: str, *, confidence: float, evidence: str = "") -> None:
        self._hallucinations.append(
            {"target": target, "confidence": confidence, "evidence": evidence, "ts": now()}
        )

    def record_retrieval(self, quality: float) -> None:
        self._retrieval_qualities.append(max(0.0, min(1.0, quality)))

    def record_planner(self, quality: float) -> None:
        self._planner_qualities.append(max(0.0, min(1.0, quality)))

    def record_tool(self, success: bool) -> None:
        self._tool_successes.append(success)

    def record_workflow(self, success: bool) -> None:
        self._workflow_successes.append(success)

    # ---- reporting --------------------------------------------------

    def summary(self) -> Dict[str, Any]:
        return {
            "feedback_count": len(self._feedback),
            "feedback_avg": self._avg([f.rating for f in self._feedback]),
            "failures": len(self._failures),
            "latency_avg_ms": self._avg(self._latencies),
            "hallucinations": len(self._hallucinations),
            "retrieval_quality": self._avg(self._retrieval_qualities),
            "planner_quality": self._avg(self._planner_qualities),
            "tool_success_rate": self._rate(self._tool_successes),
            "workflow_success_rate": self._rate(self._workflow_successes),
        }

    def improvement_report(self) -> Dict[str, Any]:
        """Generate a report with recommended improvements based on observed signals."""

        recommendations: List[str] = []
        retrieval = self._avg(self._retrieval_qualities)
        planner = self._avg(self._planner_qualities)
        tool_success = self._rate(self._tool_successes)
        workflow_success = self._rate(self._workflow_successes)
        feedback_avg = self._avg([f.rating for f in self._feedback])
        latency = self._avg(self._latencies)
        hallucination_rate = (
            len(self._hallucinations) / max(len(self._feedback), 1)
        )

        if retrieval is not None and retrieval < 0.6:
            recommendations.append("Improve retrieval quality: add query rewriting or hybrid search.")
        if planner is not None and planner < 0.6:
            recommendations.append("Planner quality is low: review cost estimator and replanning logic.")
        if tool_success is not None and tool_success < 0.7:
            recommendations.append("Tool success rate is low: add retries and better error handling.")
        if workflow_success is not None and workflow_success < 0.7:
            recommendations.append("Workflow success is low: enable rollback and approval gates.")
        if feedback_avg is not None and feedback_avg < 0.2:
            recommendations.append("User feedback is negative: collect more granular signals.")
        if latency is not None and latency > 4000:
            recommendations.append("Latency is high: enable caching and async I/O.")
        if hallucination_rate > 0.1:
            recommendations.append("Hallucinations detected: tighten verification strategy.")

        return {
            "generated_at": now(),
            "metrics": self.summary(),
            "recommendations": recommendations or ["No critical issues detected."],
        }

    def _avg(self, values: List[float]) -> Optional[float]:
        if not values:
            return None
        return sum(values) / len(values)

    def _rate(self, values: List[bool]) -> Optional[float]:
        if not values:
            return None
        return sum(1 for v in values if v) / len(values)


_GLOBAL_ENGINE: Optional[LearningEngine] = None


def get_learning_engine() -> LearningEngine:
    global _GLOBAL_ENGINE
    if _GLOBAL_ENGINE is None:
        _GLOBAL_ENGINE = LearningEngine()
    return _GLOBAL_ENGINE