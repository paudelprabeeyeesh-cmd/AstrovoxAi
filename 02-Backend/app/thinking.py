import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from app.intelligence.execution_tracer import ExecutionTracer, TraceEventType

logger = logging.getLogger(__name__)


@dataclass
class ReasoningTrace:
    step: str
    thought: str
    evidence: List[str] = field(default_factory=list)
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ThinkingConfig:
    def __init__(
        self,
        enabled: bool = False,
        effort: str = "medium",
        max_tokens: Optional[int] = None,
        budget_tokens: Optional[int] = None,
        trace: Optional[ExecutionTracer] = None,
        request_id: Optional[str] = None,
    ):
        self.enabled = enabled
        self.effort = effort
        self.max_tokens = max_tokens
        self.budget_tokens = budget_tokens
        self.trace = trace
        self.request_id = request_id
        self.steps: List[ReasoningTrace] = []

    def add_step(
        self,
        step: str,
        thought: str,
        evidence: Optional[List[str]] = None,
        confidence: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        rs = ReasoningTrace(
            step=step,
            thought=thought,
            evidence=evidence or [],
            confidence=confidence,
            metadata=metadata or {},
        )
        self.steps.append(rs)
        if self.trace and self.request_id:
            self.trace.trace_reasoning_step(
                request_id=self.request_id,
                step=step,
                thought=thought,
                evidence=evidence,
                confidence=confidence,
                metadata=metadata,
            )

    def to_anthropic_params(self) -> dict:
        if not self.enabled:
            return {}
        params = {"type": "enabled"}
        if self.effort == "low":
            params["budget_tokens"] = self.budget_tokens or 1024
        elif self.effort == "medium":
            params["budget_tokens"] = self.budget_tokens or 4096
        elif self.effort == "high":
            params["budget_tokens"] = self.budget_tokens or 16384
        if self.max_tokens:
            params["max_tokens"] = self.max_tokens
        return params

    def to_openai_params(self) -> dict:
        if not self.enabled:
            return {}
        effort_map = {"low": "low", "medium": "medium", "high": "high"}
        return {"reasoning_effort": effort_map.get(self.effort, "medium")}

    def get_summary(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "effort": self.effort,
            "steps_recorded": len(self.steps),
            "steps": [
                {
                    "step": s.step,
                    "thought": s.thought,
                    "confidence": s.confidence,
                    "evidence": s.evidence,
                }
                for s in self.steps
            ],
        }


def get_thinking_config(
    effort: str = "medium",
    enabled: bool = True,
    trace: Optional[ExecutionTracer] = None,
    request_id: Optional[str] = None,
) -> ThinkingConfig:
    return ThinkingConfig(
        enabled=enabled,
        effort=effort,
        trace=trace,
        request_id=request_id,
    )
