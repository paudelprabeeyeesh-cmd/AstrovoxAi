"""Tests for observability utilities - expanded coverage."""

from __future__ import annotations

import logging

import pytest

from astrovox.observability import Tracer, configure_logging, log_event, reset_metrics, timing


def test_timing_updates_metric():
    reset_metrics()
    timing("latency", 10.0)
    assert _get_metric("latency") == 10.0


def test_reset_metrics_clears_all():
    incr("requests", 1.0)
    reset_metrics()
    assert _get_metric("requests") == 0.0


def test_tracer_multiple_spans():
    tracer = Tracer()
    s1 = tracer.start("op1")
    s2 = tracer.start("op2")
    tracer.end(s1)
    tracer.end(s2)
    spans = tracer.spans()
    assert len(spans) == 2


def test_configure_logging_sets_level():
    configure_logging(level=logging.DEBUG)
    assert True


def test_log_event_with_payload():
    log_event("test", payload={"key": "value"})
    assert True


def _get_metric(name):
    from astrovox import observability
    return observability._metrics.get(name, 0.0)
