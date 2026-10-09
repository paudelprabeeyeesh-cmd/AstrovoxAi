from unittest.mock import patch

from performance_optimization.memory_optimizer import (
    MemorySnapshot,
    compress_references,
    describe,
    drop_references,
    optimize_memory,
    report_memory,
    take_snapshot,
    to_json,
)


def test_take_snapshot_returns_snapshot():
    with patch("performance_optimization.memory_optimizer._rss_mb", return_value=10.0), \
         patch("performance_optimization.memory_optimizer._allocations", return_value=100), \
         patch("performance_optimization.memory_optimizer._references", return_value=50):
        snapshot = take_snapshot()
    assert isinstance(snapshot, MemorySnapshot)
    assert snapshot.rss_mb == 10.0
    assert snapshot.allocations == 100
    assert snapshot.references == 50


def test_drop_references_clears_objects():
    data = [{"a": 1}, [1, 2, 3]]
    drop_references(data)
    assert data[0] == {}
    assert data[1] == []


def test_compress_references_returns_non_negative():
    obj = [1, 2, 3]
    saved = compress_references(obj)
    assert saved is None or saved >= 0


def test_report_memory_format():
    snapshot = MemorySnapshot(rss_mb=10.5, allocations=100, references=50)
    report = report_memory(snapshot)
    assert "10.50 MB" in report
    assert "100" in report
    assert "50" in report


def test_to_json_serializable():
    snapshot = MemorySnapshot(rss_mb=10.0, allocations=100, references=50)
    json_str = to_json(snapshot)
    assert "rss_mb" in json_str
    assert "10.0" in json_str


def test_describe_returns_string():
    assert isinstance(describe(), str)
    assert "Memory optimizer" in describe()


def test_optimize_memory_returns_result_and_metrics():
    with patch("performance_optimization.memory_optimizer.take_snapshot") as mock_snap, \
         patch("performance_optimization.memory_optimizer.drop_references") as mock_drop:
        def func():
            return 42
        mock_snap.side_effect = [
            MemorySnapshot(rss_mb=10.0, allocations=100, references=50),
            MemorySnapshot(rss_mb=10.0, allocations=100, references=50),
            MemorySnapshot(rss_mb=9.0, allocations=90, references=40),
            MemorySnapshot(rss_mb=8.0, allocations=80, references=30),
        ]
        result, metrics = optimize_memory(func, [{"a": 1}])
    assert result == 42
    assert "rss_mb" in metrics
    assert "allocations" in metrics
    assert "rss_delta" in metrics
    assert "allocations_delta" in metrics
