"""
Execution Tracer - Phase 2.13

Provides explainability by tracking and exposing:
- Which documents were referenced
- Which tools were used
- Why a model was selected
- Confidence level
- Sources consulted
- Execution timeline
- Decision points
- Reasoning steps and chain-of-thought
"""

from typing import Any, Dict, List, Optional
from enum import Enum
from datetime import datetime
from dataclasses import dataclass


class TraceEventType(str, Enum):
    REQUEST_RECEIVED = "request_received"
    MODEL_SELECTED = "model_selected"
    INTENT_DETECTED = "intent_detected"
    CONTEXT_RETRIEVED = "context_retrieved"
    TOOL_CALLED = "tool_called"
    TOOL_COMPLETED = "tool_completed"
    PLAN_GENERATED = "plan_generated"
    PLAN_EXECUTED = "plan_executed"
    RESPONSE_GENERATED = "response_generated"
    ERROR_OCCURRED = "error_occurred"
    REASONING_STEP = "reasoning_step"
    CONTEXT_COMPRESSED = "context_compressed"
    SELF_CORRECTION = "self_correction"
    MODEL_FALLBACK = "model_fallback"


@dataclass
class ReasoningStep:
    step: str
    thought: str
    evidence: List[str] = None
    confidence: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.evidence is None:
            self.evidence = []
        if self.metadata is None:
            self.metadata = {}


class TraceEvent:
    def __init__(
        self,
        event_type: TraceEventType,
        timestamp: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.event_type = event_type
        self.timestamp = timestamp
        self.data = data
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "data": self.data,
            "metadata": self.metadata,
        }


class ExecutionTrace:
    def __init__(self, request_id: str, user_id: int, user_message: str):
        self.request_id = request_id
        self.user_id = user_id
        self.user_message = user_message
        self.events: List[TraceEvent] = []
        self.reasoning_steps: List[ReasoningStep] = []
        self.start_time = datetime.utcnow().isoformat()
        self.end_time: Optional[str] = None
        self.final_response: Optional[str] = None
        self.metadata: Dict[str, Any] = {}

    def add_event(
        self,
        event_type: TraceEventType,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ):
        event = TraceEvent(
            event_type=event_type,
            timestamp=datetime.utcnow().isoformat(),
            data=data,
            metadata=metadata or {},
        )
        self.events.append(event)

    def add_reasoning_step(
        self,
        step: str,
        thought: str,
        evidence: Optional[List[str]] = None,
        confidence: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        rs = ReasoningStep(
            step=step,
            thought=thought,
            evidence=evidence or [],
            confidence=confidence,
            metadata=metadata or {},
        )
        self.reasoning_steps.append(rs)
        self.add_event(
            TraceEventType.REASONING_STEP,
            {
                "step": step,
                "thought": thought,
                "confidence": confidence,
            },
            metadata={"evidence": evidence or [], **rs.metadata},
        )

    def complete(self, final_response: str):
        self.end_time = datetime.utcnow().isoformat()
        self.final_response = final_response

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "user_message": self.user_message,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self._calculate_duration(),
            "final_response": self.final_response,
            "events": [event.to_dict() for event in self.events],
            "reasoning_chain": [
                {
                    "step": rs.step,
                    "thought": rs.thought,
                    "evidence": rs.evidence,
                    "confidence": rs.confidence,
                    "metadata": rs.metadata,
                }
                for rs in self.reasoning_steps
            ],
            "metadata": self.metadata,
            "summary": self._generate_summary(),
        }

    def _calculate_duration(self) -> Optional[int]:
        if not self.end_time:
            return None
        start = datetime.fromisoformat(self.start_time)
        end = datetime.fromisoformat(self.end_time)
        return int((end - start).total_seconds() * 1000)

    def _generate_summary(self) -> Dict[str, Any]:
        summary: Dict[str, Any] = {
            "total_events": len(self.events),
            "model_used": None,
            "intent_detected": None,
            "tools_used": [],
            "documents_referenced": [],
            "errors": [],
            "reasoning_steps": len(self.reasoning_steps),
        }
        for event in self.events:
            if event.event_type == TraceEventType.MODEL_SELECTED:
                summary["model_used"] = event.data.get("model_name")
                summary["model_selection_reason"] = event.data.get("reason")
            elif event.event_type == TraceEventType.INTENT_DETECTED:
                summary["intent_detected"] = event.data.get("intent")
            elif event.event_type == TraceEventType.TOOL_CALLED:
                summary["tools_used"].append(
                    {
                        "tool": event.data.get("tool"),
                        "parameters": event.data.get("parameters"),
                        "timestamp": event.timestamp,
                    }
                )
            elif event.event_type == TraceEventType.CONTEXT_RETRIEVED:
                docs = event.data.get("documents", [])
                summary["documents_referenced"].extend(docs)
            elif event.event_type == TraceEventType.ERROR_OCCURRED:
                summary["errors"].append(
                    {
                        "error": event.data.get("error"),
                        "timestamp": event.timestamp,
                    }
                )
        return summary

    def get_explanation(self) -> str:
        lines = [
            f"Execution Trace for Request: {self.request_id}",
            f"User Message: {self.user_message}",
            f"Duration: {self._calculate_duration()}ms" if self._calculate_duration() else "Duration: In progress",
            "",
            "Execution Steps:",
        ]
        for event in self.events:
            lines.append(f"  [{event.timestamp}] {event.event_type.value}")
            if event.data:
                for key, value in event.data.items():
                    lines.append(f"    {key}: {value}")
        if self.final_response:
            lines.append("")
            lines.append("Final Response:")
            lines.append(f"  {self.final_response[:200]}...")
        return "\n".join(lines)


class ExecutionTracer:
    def __init__(self):
        self.traces: Dict[str, ExecutionTrace] = {}
        self.active_traces: Dict[str, ExecutionTrace] = {}

    def start_trace(
        self,
        request_id: str,
        user_id: int,
        user_message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExecutionTrace:
        trace = ExecutionTrace(request_id, user_id, user_message)
        trace.metadata = metadata or {}
        trace.add_event(
            TraceEventType.REQUEST_RECEIVED,
            {"user_message": user_message, "user_id": user_id},
        )
        self.traces[request_id] = trace
        self.active_traces[request_id] = trace
        return trace

    def get_trace(self, request_id: str) -> Optional[ExecutionTrace]:
        return self.traces.get(request_id)

    def end_trace(self, request_id: str, final_response: str):
        trace = self.get_trace(request_id)
        if trace:
            trace.complete(final_response)
            self.active_traces.pop(request_id, None)

    def add_trace_event(
        self,
        request_id: str,
        event_type: TraceEventType,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ):
        trace = self.get_trace(request_id)
        if trace:
            trace.add_event(event_type, data, metadata)

    def trace_model_selection(
        self,
        request_id: str,
        model_name: str,
        reason: str,
        alternatives: Optional[List[str]] = None,
    ):
        self.add_trace_event(
            request_id,
            TraceEventType.MODEL_SELECTED,
            {
                "model_name": model_name,
                "reason": reason,
                "alternatives": alternatives or [],
            },
        )

    def trace_intent_detection(
        self,
        request_id: str,
        intent: str,
        confidence: float,
    ):
        self.add_trace_event(
            request_id,
            TraceEventType.INTENT_DETECTED,
            {
                "intent": intent,
                "confidence": confidence,
            },
        )

    def trace_context_retrieval(
        self,
        request_id: str,
        sources: List[str],
        documents: List[str],
    ):
        self.add_trace_event(
            request_id,
            TraceEventType.CONTEXT_RETRIEVED,
            {
                "sources": sources,
                "documents": documents,
            },
        )

    def trace_tool_call(
        self,
        request_id: str,
        tool: str,
        parameters: Dict[str, Any],
    ):
        self.add_trace_event(
            request_id,
            TraceEventType.TOOL_CALLED,
            {
                "tool": tool,
                "parameters": parameters,
            },
        )

    def trace_tool_completion(
        self,
        request_id: str,
        tool: str,
        result: Any,
        success: bool,
    ):
        self.add_trace_event(
            request_id,
            TraceEventType.TOOL_COMPLETED,
            {
                "tool": tool,
                "result": result,
                "success": success,
            },
        )

    def trace_plan_generation(
        self,
        request_id: str,
        plan_id: str,
        steps: List[Dict[str, Any]],
    ):
        self.add_trace_event(
            request_id,
            TraceEventType.PLAN_GENERATED,
            {
                "plan_id": plan_id,
                "steps": steps,
            },
        )

    def trace_plan_execution(
        self,
        request_id: str,
        plan_id: str,
        success: bool,
    ):
        self.add_trace_event(
            request_id,
            TraceEventType.PLAN_EXECUTED,
            {
                "plan_id": plan_id,
                "success": success,
            },
        )

    def trace_error(
        self,
        request_id: str,
        error: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        self.add_trace_event(
            request_id,
            TraceEventType.ERROR_OCCURRED,
            {
                "error": error,
                "context": context or {},
            },
        )

    def trace_response_generation(
        self,
        request_id: str,
        format: str,
        tokens_used: int,
    ):
        self.add_trace_event(
            request_id,
            TraceEventType.RESPONSE_GENERATED,
            {
                "format": format,
                "tokens_used": tokens_used,
            },
        )

    def trace_reasoning_step(
        self,
        request_id: str,
        step: str,
        thought: str,
        evidence: Optional[List[str]] = None,
        confidence: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        trace = self.get_trace(request_id)
        if trace:
            trace.add_reasoning_step(
                step=step,
                thought=thought,
                evidence=evidence,
                confidence=confidence,
                metadata=metadata,
            )

    def trace_context_compression(
        self,
        request_id: str,
        original_tokens: int,
        compressed_tokens: int,
        strategy: str,
    ):
        self.add_trace_event(
            request_id,
            TraceEventType.CONTEXT_COMPRESSED,
            {
                "original_tokens": original_tokens,
                "compressed_tokens": compressed_tokens,
                "strategy": strategy,
                "compression_ratio": compressed_tokens / max(original_tokens, 1),
            },
        )

    def trace_self_correction(
        self,
        request_id: str,
        pass_number: int,
        issues: List[str],
        corrected: bool,
    ):
        self.add_trace_event(
            request_id,
            TraceEventType.SELF_CORRECTION,
            {
                "pass_number": pass_number,
                "issues": issues,
                "corrected": corrected,
            },
        )

    def trace_model_fallback(
        self,
        request_id: str,
        from_model: str,
        to_model: str,
        reason: str,
    ):
        self.add_trace_event(
            request_id,
            TraceEventType.MODEL_FALLBACK,
            {
                "from_model": from_model,
                "to_model": to_model,
                "reason": reason,
            },
        )

    def get_user_traces(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        user_traces = [
            trace for trace in self.traces.values()
            if trace.user_id == user_id
        ]
        user_traces.sort(key=lambda t: t.start_time, reverse=True)
        return [trace.to_dict() for trace in user_traces[:limit]]

    def get_trace_summary(self, request_id: str) -> Optional[Dict[str, Any]]:
        trace = self.get_trace(request_id)
        if not trace:
            return None
        return trace._generate_summary()

    def get_trace_explanation(self, request_id: str) -> Optional[str]:
        trace = self.get_trace(request_id)
        if not trace:
            return None
        return trace.get_explanation()

    def cleanup_old_traces(self, max_age_hours: int = 24):
        cutoff = datetime.utcnow().timestamp() - (max_age_hours * 3600)
        to_remove = []
        for request_id, trace in self.traces.items():
            trace_time = datetime.fromisoformat(trace.start_time).timestamp()
            if trace_time < cutoff:
                to_remove.append(request_id)
        for request_id in to_remove:
            del self.traces[request_id]
            self.active_traces.pop(request_id, None)
        return len(to_remove)
