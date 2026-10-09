"""Tests for reasoning traces."""

import pytest

from app.intelligence.execution_tracer import (
    ExecutionTracer,
    ExecutionTrace,
    TraceEventType,
    ReasoningStep,
)
from app.thinking import ThinkingConfig, get_thinking_config


class TestReasoningStep:
    def test_defaults(self):
        rs = ReasoningStep(step="plan", thought="think")
        assert rs.evidence == []
        assert rs.confidence == 0.0
        assert rs.metadata == {}

    def test_post_init(self):
        rs = ReasoningStep(step="plan", thought="think", evidence=["a"], confidence=0.8, metadata={"k": "v"})
        assert rs.evidence == ["a"]
        assert rs.confidence == 0.8
        assert rs.metadata == {"k": "v"}


class TestExecutionTrace:
    def test_add_event_and_to_dict(self):
        trace = ExecutionTrace(request_id="r1", user_id=1, user_message="hi")
        trace.add_event(TraceEventType.MODEL_SELECTED, {"model_name": "gpt-4"})
        d = trace.to_dict()
        assert d["request_id"] == "r1"
        assert len(d["events"]) == 1

    def test_add_reasoning_step(self):
        trace = ExecutionTrace(request_id="r1", user_id=1, user_message="hi")
        trace.add_reasoning_step(step="plan", thought="think", evidence=["a"], confidence=0.8)
        assert len(trace.reasoning_steps) == 1
        assert trace.reasoning_steps[0].step == "plan"
        d = trace.to_dict()
        assert d["reasoning_chain"][0]["thought"] == "think"

    def test_complete_sets_end_time(self):
        trace = ExecutionTrace(request_id="r1", user_id=1, user_message="hi")
        trace.complete("ok")
        assert trace.end_time is not None
        assert trace.final_response == "ok"


class TestExecutionTracer:
    def test_start_and_get(self):
        tracer = ExecutionTracer()
        trace = tracer.start_trace(request_id="r1", user_id=1, user_message="hi")
        assert tracer.get_trace("r1") is trace

    def test_end_trace(self):
        tracer = ExecutionTracer()
        tracer.start_trace(request_id="r1", user_id=1, user_message="hi")
        tracer.end_trace("r1", "done")
        assert tracer.get_trace("r1").final_response == "done"

    def test_trace_model_selection(self):
        tracer = ExecutionTracer()
        tracer.start_trace(request_id="r1", user_id=1, user_message="hi")
        tracer.trace_model_selection(request_id="r1", model_name="gpt-4", reason="quality")
        trace = tracer.get_trace("r1")
        assert any(e.data.get("model_name") == "gpt-4" for e in trace.events)

    def test_trace_reasoning_step(self):
        tracer = ExecutionTracer()
        tracer.start_trace(request_id="r1", user_id=1, user_message="hi")
        tracer.trace_reasoning_step(request_id="r1", step="plan", thought="think", confidence=0.9)
        trace = tracer.get_trace("r1")
        assert len(trace.reasoning_steps) == 1
        assert trace.reasoning_steps[0].step == "plan"

    def test_trace_context_compression(self):
        tracer = ExecutionTracer()
        tracer.start_trace(request_id="r1", user_id=1, user_message="hi")
        tracer.trace_context_compression(request_id="r1", original_tokens=100, compressed_tokens=80, strategy="hybrid")
        trace = tracer.get_trace("r1")
        assert any(e.event_type == TraceEventType.CONTEXT_COMPRESSED for e in trace.events)

    def test_trace_self_correction(self):
        tracer = ExecutionTracer()
        tracer.start_trace(request_id="r1", user_id=1, user_message="hi")
        tracer.trace_self_correction(request_id="r1", pass_number=1, issues=["too_long"], corrected=True)
        trace = tracer.get_trace("r1")
        assert any(e.event_type == TraceEventType.SELF_CORRECTION for e in trace.events)

    def test_trace_model_fallback(self):
        tracer = ExecutionTracer()
        tracer.start_trace(request_id="r1", user_id=1, user_message="hi")
        tracer.trace_model_fallback(request_id="r1", from_model="gpt-4", to_model="gpt-4-turbo", reason="timeout")
        trace = tracer.get_trace("r1")
        assert any(e.event_type == TraceEventType.MODEL_FALLBACK for e in trace.events)

    def test_cleanup_old_traces(self):
        tracer = ExecutionTracer()
        import time
        old_id = "old"
        tracer.start_trace(request_id=old_id, user_id=1, user_message="hi")
        tracer.traces[old_id].start_time = "2000-01-01T00:00:00"
        removed = tracer.cleanup_old_traces(max_age_hours=1)
        assert removed >= 1
        assert tracer.get_trace(old_id) is None


class TestThinkingConfig:
    def test_defaults(self):
        cfg = ThinkingConfig()
        assert cfg.enabled is False
        assert cfg.effort == "medium"
        assert cfg.steps == []

    def test_add_step_records_trace(self):
        tracer = ExecutionTracer()
        tracer.start_trace(request_id="r1", user_id=1, user_message="hi")
        cfg = ThinkingConfig(enabled=True, trace=tracer, request_id="r1")
        cfg.add_step("plan", "think", confidence=0.8)
        assert len(cfg.steps) == 1
        assert len(tracer.get_trace("r1").reasoning_steps) == 1

    def test_to_anthropic_params(self):
        cfg = ThinkingConfig(enabled=True, effort="medium", budget_tokens=4096)
        params = cfg.to_anthropic_params()
        assert params["type"] == "enabled"
        assert params["budget_tokens"] == 4096

    def test_to_openai_params(self):
        cfg = ThinkingConfig(enabled=True, effort="high")
        params = cfg.to_openai_params()
        assert params["reasoning_effort"] == "high"

    def test_get_summary(self):
        cfg = ThinkingConfig(enabled=True)
        cfg.add_step("plan", "think")
        summary = cfg.get_summary()
        assert summary["enabled"] is True
        assert summary["steps_recorded"] == 1
