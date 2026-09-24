"""Tests for Task 114: Forensic Analysis."""

import time

import numpy as np
import pytest

from security_audit.forensic_analysis import (
    EvidenceItem,
    ForensicCollector,
    ForensicReport,
    TimelineEvent,
)


@pytest.fixture
def collector():
    return ForensicCollector(case_id="TEST-001")


class TestEvidenceItem:
    def test_collect_bytes(self, collector):
        item = collector.collect("memory", b"raw data here")
        assert isinstance(item, EvidenceItem)
        assert item.data == b"raw data here"
        assert len(item.hash_sha256) == 64

    def test_collect_text(self, collector):
        item = collector.collect_text("log", "some log entry")
        assert item.data == b"some log entry"

    def test_verify_integrity_valid(self, collector):
        item = collector.collect("disk", b"important data")
        assert collector.verify_integrity(item) is True

    def test_verify_integrity_tampered(self, collector):
        item = collector.collect("disk", b"important data")
        item.data = b"tampered data"
        assert collector.verify_integrity(item) is False


class TestForensicCollector:
    def test_case_id_default(self):
        c = ForensicCollector()
        assert c.case_id.startswith("FOR-")

    def test_collect_increments_id(self, collector):
        item1 = collector.collect("source1", b"data1")
        item2 = collector.collect("source2", b"data2")
        assert item1.evidence_id != item2.evidence_id

    def test_build_timeline_sorted(self, collector):
        events = [
            TimelineEvent(timestamp=3.0, source="a", event="c", significance=1.0),
            TimelineEvent(timestamp=1.0, source="b", event="a", significance=0.5),
            TimelineEvent(timestamp=2.0, source="c", event="b", significance=0.8),
        ]
        timeline = collector.build_timeline(events)
        assert [e.timestamp for e in timeline] == [1.0, 2.0, 3.0]

    def test_analyze_patterns_empty(self, collector):
        patterns = collector.analyze_patterns([])
        assert patterns["event_count"] == 0

    def test_analyze_patterns_populated(self, collector):
        now = time.time()
        events = [TimelineEvent(timestamp=now + i, source="s", event="e", significance=float(i % 5)) for i in range(20)]
        patterns = collector.analyze_patterns(events)
        assert patterns["event_count"] == 20
        assert 0.0 <= patterns["mean_significance"] <= 5.0

    def test_generate_report(self, collector):
        now = time.time()
        events = [TimelineEvent(timestamp=now + i, source="s", event="e", significance=0.5) for i in range(5)]
        report = collector.generate_report(events)
        assert isinstance(report, ForensicReport)
        assert report.case_id == "TEST-001"
        assert report.evidence_count >= 0

    def test_report_integrity_verified_empty(self, collector):
        now = time.time()
        events = [TimelineEvent(timestamp=now, source="s", event="e", significance=0.5)]
        report = collector.generate_report(events)
        assert report.integrity_verified is True

    def test_hash_changes_with_data(self):
        c1 = ForensicCollector(case_id="HASH-1")
        c2 = ForensicCollector(case_id="HASH-2")
        c1.collect("s", b"data")
        c2.collect("s", b"other")
        assert c1._evidence[0].hash_sha256 != c2._evidence[0].hash_sha256


class TestForensicAnalysisNumpy:
    def test_significance_array_dtype(self, collector):
        now = time.time()
        events = [TimelineEvent(timestamp=now + i, source="s", event="e", significance=float(i)) for i in range(10)]
        significances = np.array([e.significance for e in events], dtype=np.float64)
        assert significances.dtype in (np.float64, np.float32)

    def test_patterns_mean_in_range(self, collector):
        events = [TimelineEvent(timestamp=time.time() + i, source="s", event="e", significance=float(i % 10)) for i in range(20)]
        patterns = collector.analyze_patterns(events)
        assert 0.0 <= patterns["mean_significance"] <= 10.0

    def test_multiple_collect_items(self, collector):
        for i in range(10):
            collector.collect(f"source{i}", f"data{i}".encode())
        assert len(collector._evidence) == 10
        hashes = np.array([len(e.hash_sha256) for e in collector._evidence])
        assert len(hashes) == 10

    def test_event_count_in_report(self, collector):
        now = time.time()
        events = [TimelineEvent(timestamp=now + i, source="s", event="e", significance=0.5) for i in range(15)]
        report = collector.generate_report(events)
        assert len(report.timeline_events) == 15


def hashlib_ish(s: str) -> int:
    return len(s)
