"""AI evaluation framework.

Records per-response evaluation signals: hallucination risk, citation
quality, retrieval precision, latency, and cost.
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class Evaluation:
    id: str
    request_id: str
    workspace_id: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    hallucination_risk: float = 0.0
    citation_quality: float = 0.0
    tool_success_rate: float = 0.0
    retrieval_precision: float = 0.0
    response_latency_ms: float = 0.0
    user_feedback: Optional[float] = None
    cost: float = 0.0
    agent_success: Optional[bool] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "request_id": self.request_id,
            "workspace_id": self.workspace_id,
            "created_at": self.created_at,
            "hallucination_risk": round(self.hallucination_risk, 4),
            "citation_quality": round(self.citation_quality, 4),
            "tool_success_rate": round(self.tool_success_rate, 4),
            "retrieval_precision": round(self.retrieval_precision, 4),
            "response_latency_ms": round(self.response_latency_ms, 2),
            "user_feedback": self.user_feedback,
            "cost": round(self.cost, 6),
            "agent_success": self.agent_success,
            "metadata": self.metadata,
        }


class EvaluationStore:
    """Records and aggregates evaluations."""

    def __init__(self, history: int = 5000) -> None:
        self._records: List[Evaluation] = []
        self._history = history
        self._index: Dict[str, List[Evaluation]] = defaultdict(list)

    def record(self, evaluation: Evaluation) -> Evaluation:
        self._records.append(evaluation)
        if len(self._records) > self._history:
            self._records = self._records[-self._history :]
        self._index[evaluation.workspace_id].append(evaluation)
        return evaluation

    def make(
        self,
        request_id: str,
        workspace_id: str,
        **fields: Any,
    ) -> Evaluation:
        ev = Evaluation(
            id=f"ev_{uuid.uuid4().hex[:10]}",
            request_id=request_id,
            workspace_id=workspace_id,
            **fields,
        )
        return self.record(ev)

    def list(
        self, workspace_id: Optional[str] = None, limit: int = 100
    ) -> List[Evaluation]:
        items = (
            self._index.get(workspace_id, []) if workspace_id else list(self._records)
        )
        return list(items[-limit:])

    def summary(self, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        items = self.list(workspace_id, limit=10_000)
        if not items:
            return {"count": 0}
        n = len(items)
        return {
            "count": n,
            "hallucination_risk": round(sum(e.hallucination_risk for e in items) / n, 4),
            "citation_quality": round(sum(e.citation_quality for e in items) / n, 4),
            "tool_success_rate": round(sum(e.tool_success_rate for e in items) / n, 4),
            "retrieval_precision": round(sum(e.retrieval_precision for e in items) / n, 4),
            "response_latency_ms": round(
                sum(e.response_latency_ms for e in items) / n, 2
            ),
            "cost": round(sum(e.cost for e in items), 6),
            "user_feedback": round(
                sum(e.user_feedback for e in items if e.user_feedback is not None)
                / max(1, sum(1 for e in items if e.user_feedback is not None)),
                4,
            )
            if any(e.user_feedback is not None for e in items)
            else None,
        }


_GLOBAL_STORE: Optional[EvaluationStore] = None


def get_evaluation_store() -> EvaluationStore:
    global _GLOBAL_STORE
    if _GLOBAL_STORE is None:
        _GLOBAL_STORE = EvaluationStore()
    return _GLOBAL_STORE


def record_evaluation(
    request_id: str,
    workspace_id: str,
    **fields: Any,
) -> Evaluation:
    return get_evaluation_store().make(request_id, workspace_id, **fields)