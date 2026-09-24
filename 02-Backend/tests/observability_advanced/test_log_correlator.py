import pytest

from advanced_backend.observability_advanced.log_correlator import LogCorrelator


def test_correlate_by_request_id_groups_logs():
    correlator = LogCorrelator()
    correlator.load([
        {"request_id": "r1", "message": "start"},
        {"request_id": "r2", "message": "start"},
        {"request_id": "r1", "message": "end"},
        {"request_id": None, "message": "heartbeat"},
    ])
    grouped = correlator.correlate_by_request_id()
    assert len(grouped["r1"]) == 2
    assert len(grouped["r2"]) == 1
    assert None in grouped
    assert len(grouped[None]) == 1


def test_search_matches_values():
    correlator = LogCorrelator()
    correlator.load([
        {"request_id": "r1", "message": "timeout"},
        {"request_id": "r2", "message": "ok"},
    ])
    results = correlator.search("timeout")
    assert len(results) == 1
    assert results[0]["request_id"] == "r1"


def test_search_no_match():
    correlator = LogCorrelator()
    correlator.load([
        {"request_id": "r1", "message": "ok"},
    ])
    assert correlator.search("missing") == []


def test_load_replaces_previous_logs():
    correlator = LogCorrelator()
    correlator.load([{"request_id": "r1"}])
    correlator.load([{"request_id": "r2"}])
    grouped = correlator.correlate_by_request_id()
    assert len(grouped) == 1
    assert "r1" not in grouped
