import numpy as np
import pytest

from observability.tracing import (
    Span,
    Tracer,
    TraceContext,
    get_trace_context,
)


def test_span_duration_ms_none_when_open():
    span = Span(
        span_id="s1",
        trace_id="t1",
        parent_span_id=None,
        operation="op",
        start_time=0.0,
    )
    assert span.duration_ms is None


def test_span_duration_ms():
    span = Span(
        span_id="s1",
        trace_id="t1",
        parent_span_id=None,
        operation="op",
        start_time=0.0,
        end_time=0.05,
    )
    assert span.duration_ms == pytest.approx(50.0)


def test_tracer_start_span():
    tracer = Tracer()
    span = tracer.start_span("op")
    assert span.operation == "op"
    assert span.span_id is not None
    assert span.trace_id is not None


def test_tracer_end_span():
    tracer = Tracer()
    span = tracer.start_span("op")
    tracer.end_span(span)
    assert span.duration_ms is not None


def test_tracer_parent_span_propagation():
    tracer = Tracer()
    parent = tracer.start_span("parent")
    child = tracer.start_span("child", parent_span=parent)
    assert child.trace_id == parent.trace_id
    assert child.parent_span_id == parent.span_id


def test_tracer_span_contextmanager():
    tracer = Tracer()
    with tracer.span("op") as span:
        assert span.operation == "op"
    assert span.duration_ms is not None


def test_get_trace_context_singleton():
    tc1 = get_trace_context()
    tc2 = get_trace_context()
    assert tc1 is tc2


def test_trace_context_get_current_span_none():
    tc = TraceContext()
    assert tc.get_current_span() is None


def test_trace_context_set_and_get():
    tc = TraceContext()
    span = Span(
        span_id="s1",
        trace_id="t1",
        parent_span_id=None,
        operation="op",
        start_time=0.0,
    )
    tc.set_current_span(span)
    assert tc.get_current_span() is span
    tc.set_current_span(None)
    assert tc.get_current_span() is None


def test_trace_context_get_trace_id():
    tc = TraceContext()
    assert tc.get_trace_id() is None
    span = Span(
        span_id="s1",
        trace_id="t1",
        parent_span_id=None,
        operation="op",
        start_time=0.0,
    )
    tc.set_current_span(span)
    assert tc.get_trace_id() == "t1"


def test_tracer_get_trace():
    tracer = Tracer()
    s1 = tracer.start_span("op")
    tracer.end_span(s1)
    trace = tracer.get_trace(s1.trace_id)
    assert len(trace) == 1
    assert trace[0].span_id == s1.span_id


def test_tracer_export():
    tracer = Tracer()
    s = tracer.start_span("op")
    tracer.end_span(s)
    exported = tracer.export()
    assert "spans" in exported
    assert len(exported["spans"]) == 1
    e = exported["spans"][0]
    assert e["operation"] == "op"
    assert e["span_id"] == s.span_id
    assert "duration_ms" in e


def test_tracer_span_track_multiple_operations():
    tracer = Tracer()
    s1 = tracer.start_span("a")
    s2 = tracer.start_span("b")
    tracer.end_span(s1)
    tracer.end_span(s2)
    assert len(tracer.spans) == 2
    assert tracer.get_trace(s1.trace_id) == [s1]
    assert tracer.get_trace(s2.trace_id) == [s2]


def test_tracer_get_trace_empty():
    tracer = Tracer()
    assert tracer.get_trace("nonexistent") == []
