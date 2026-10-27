"""Core execution contract: every operation returns a MathResult."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class MathResult:
    """Standard result of one math engine operation.

    Attributes:
        topic_id: stable registry id, e.g. "S1.T001"
        operation_id: callable operation within the topic module
        status: implementation status (planned/scaffolded/implemented/tested/verified/blocked)
        result: the computed value (None when blocked/errored)
        explanation: human-readable derivation where supported
        steps: list of intermediate expressions/steps
        assumptions: domain restrictions and assumptions
        tolerance: numerical tolerance used, if approximate
        warnings: non-fatal warnings (e.g. ill-conditioned input)
        error: structured error message when the operation failed
        verified: whether an independent check passed
    """

    topic_id: str
    operation_id: str
    status: str = "implemented"
    result: Any = None
    explanation: str = ""
    steps: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    tolerance: Optional[float] = None
    warnings: list[str] = field(default_factory=list)
    error: Optional[str] = None
    verified: bool = False

    def ok(self) -> bool:
        return self.error is None and self.status != "blocked"

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic_id": self.topic_id,
            "operation_id": self.operation_id,
            "status": self.status,
            "result": self.result,
            "explanation": self.explanation,
            "steps": self.steps,
            "assumptions": self.assumptions,
            "tolerance": self.tolerance,
            "warnings": self.warnings,
            "error": self.error,
            "verified": self.verified,
        }
