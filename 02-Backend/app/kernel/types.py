from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .context import ContextBudget, ContextBlock
from .router import RoutingDecision


@dataclass
class KernelRequest:
    goal: str
    workspace_id: str = "default"
    user_id: str = "anonymous"
    modality: str = "text"
    metadata: Dict[str, Any] = field(default_factory=dict)
    budget: Optional[ContextBudget] = None


@dataclass
class KernelResponse:
    request_id: str
    ok: bool
    result: Any = None
    error: Optional[str] = None
    decision: Optional[RoutingDecision] = None
    context_blocks: List[ContextBlock] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)
    evaluation_id: Optional[str] = None
    elapsed_ms: float = 0.0
    cost: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "ok": self.ok,
            "result": self.result,
            "error": self.error,
            "decision": self.decision.to_dict() if self.decision else None,
            "context_blocks": [b.to_dict() for b in self.context_blocks],
            "artifacts": self.artifacts,
            "evaluation_id": self.evaluation_id,
            "elapsed_ms": round(self.elapsed_ms, 2),
            "cost": round(self.cost, 6),
        }