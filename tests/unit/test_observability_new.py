"""Tests for observability utilities."""

from __future__ import annotations

import logging

import pytest

from astrovox.observability import Tracer, gauge, incr, log_event, reset_metrics, timing


def test_incr_increments_metric():
    reset_metrics()
    incr("requests", 1.0)
    incr("requests", 2.0)
    assert _get_metric("requests") == 3.0


def test_gauge_sets_metric():
    reset_metrics()
    gauge("temperature", 72.0)
    assert _get_metric("temperature") == 72.0


def test_timing_records_duration():
    tracer = Tracer()
    span = tracer.start("op")
    tracer.end(span)
    assert span.duration_ms >= 0


def test_log_event_does_not_raise():
    log_event("test", payload={"key": "value"})


def _get_metric(name):
    from astrovox import observability
    return observability._metrics.get(name, 0.0)
