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


def test_correlate_empty_logs():
    correlator = LogCorrelator()
    correlator.load([])
    grouped = correlator.correlate_by_request_id()
    assert grouped == {}


def test_search_skips_none_values():
    correlator = LogCorrelator()
    correlator.load([
        {"request_id": "r1", "message": None},
        {"request_id": "r2", "message": "timeout"},
    ])
    results = correlator.search("timeout")
    assert len(results) == 1
    assert results[0]["request_id"] == "r2"


def test_search_with_regex_pattern():
    correlator = LogCorrelator()
    correlator.load([
        {"request_id": "r1", "message": "error 500"},
        {"request_id": "r2", "message": "error 404"},
        {"request_id": "r3", "message": "ok"},
    ])
    results = correlator.search(r"error \d+")
    assert len(results) == 2
    assert {r["request_id"] for r in results} == {"r1", "r2"}
