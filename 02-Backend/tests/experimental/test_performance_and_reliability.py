"""Tests for performance and reliability utilities."""

import pytest
import time
import asyncio
from app.response_cache_middleware import ResponseCacheMiddleware
from app.stream_buffering import StreamBuffer
from app.resource_monitor import ResourceMonitor
from app.query_plan_analyzer import QueryPlanAnalyzer
from app.db_index_recommender import DBIndexRecommender
from app.connection_reuse_checker import ConnectionReuseChecker
from app.cpu_profiler import CPUProfilerToggle
from app.memory_leak_detection import MemoryLeakDetector
from app.queue_depth_monitor import QueueDepthMonitor
from app.backpressure_handler import BackpressureHandler
from app.batch_processor import BatchProcessor, BatchResult
from app.lazy_loader import LazyLoader, LazyModuleLoader, lazy


class TestResponseCacheMiddleware:
    def test_stats(self):
        middleware = ResponseCacheMiddleware(None)
        stats = middleware.stats
        assert "hit_rate" in stats
        assert "size" in stats

    def test_clear(self):
        middleware = ResponseCacheMiddleware(None)
        middleware.clear()


class TestStreamBuffer:
    @pytest.mark.asyncio
    async def test_buffer_stream(self):
        buffer = StreamBuffer(buffer_size=10)
        async def gen():
            for i in range(3):
                yield f"chunk{i}".encode()
        chunks = []
        async for chunk in buffer.buffer_stream(gen()):
            chunks.append(chunk)
        assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_buffer_lines(self):
        buffer = StreamBuffer()
        async def gen():
            yield b"line1\nline2\nline3"
        lines = []
        async for line in buffer.buffer_lines(gen()):
            lines.append(line)
        assert len(lines) == 3

    def test_reset(self):
        buffer = StreamBuffer()
        buffer.reset()
        assert buffer._buffer_len == 0


class TestResourceMonitor:
    def test_take_snapshot(self):
        monitor = ResourceMonitor()
        snapshot = monitor.take_snapshot()
        assert "timestamp" in snapshot
        assert "cpu_percent" in snapshot

    def test_get_current(self):
        monitor = ResourceMonitor()
        current = monitor.get_current()
        assert "timestamp" in current
        assert "cpu_percent" in current

    def test_get_summary_empty(self):
        monitor = ResourceMonitor()
        summary = monitor.get_summary()
        assert summary["status"] == "no_data"


class TestQueryPlanAnalyzer:
    def test_analyze_seq_scan(self):
        analyzer = QueryPlanAnalyzer()
        plan = {"Plan": {"Node Type": "Seq Scan", "Relation Name": "users"}}
        result = analyzer.analyze(plan)
        assert result["full_scan"] is True

    def test_analyze_index_scan(self):
        analyzer = QueryPlanAnalyzer()
        plan = {"Plan": {"Node Type": "Index Scan", "Index Name": "idx_users_email"}}
        result = analyzer.analyze(plan)
        assert result["full_scan"] is False

    def test_get_history(self):
        analyzer = QueryPlanAnalyzer()
        analyzer.analyze({"Plan": {"Node Type": "Seq Scan"}})
        history = analyzer.get_history(limit=10)
        assert len(history) == 1


class TestDBIndexRecommender:
    def test_analyze_query_where(self):
        recommender = DBIndexRecommender()
        recs = recommender.analyze_query("SELECT * FROM users WHERE id = 1")
        assert any(r["reason"] == "Column used in WHERE clause" for r in recs)

    def test_analyze_query_join(self):
        recommender = DBIndexRecommender()
        recs = recommender.analyze_query("SELECT * FROM a JOIN b ON a.id = b.id")
        assert any(r["reason"] == "Column used in JOIN condition" for r in recs)

    def test_get_recommendations(self):
        recommender = DBIndexRecommender()
        recommender.analyze_query("SELECT * FROM users WHERE id = 1")
        recs = recommender.get_recommendations()
        assert len(recs) > 0


class TestConnectionReuseChecker:
    def test_register_and_release(self):
        checker = ConnectionReuseChecker()
        checker.register_connection("conn1", object())
        assert "conn1" in checker.get_active_connections()
        checker.release_connection("conn1")
        assert "conn1" not in checker.get_active_connections()

    def test_get_stats(self):
        checker = ConnectionReuseChecker()
        checker.register_connection("conn1", object())
        stats = checker.get_stats()
        assert stats["active"] == 1

    def test_clear(self):
        checker = ConnectionReuseChecker()
        checker.register_connection("conn1", object())
        checker.clear()
        assert len(checker.get_active_connections()) == 0


class TestCPUProfilerToggle:
    def test_start_stop(self):
        profiler = CPUProfilerToggle()
        profiler.start()
        result = profiler.stop(label="test")
        assert result["label"] == "test"

    def test_profile_function(self):
        profiler = CPUProfilerToggle()
        def work():
            return 42
        result = profiler.profile_function(work)
        assert result == 42

    def test_clear(self):
        profiler = CPUProfilerToggle()
        profiler.clear()


class TestMemoryLeakDetector:
    def test_detect_no_leaks(self):
        detector = MemoryLeakDetector()
        results = detector.detect("test", lambda: None)
        assert isinstance(results, list)

    def test_run_baseline(self):
        detector = MemoryLeakDetector()
        detector.run_baseline()


class TestQueueDepthMonitor:
    def test_register_and_record(self):
        monitor = QueueDepthMonitor()
        monitor.register_queue("test_queue")
        monitor.record("test_queue", 5)
        depth = monitor.get_depth("test_queue")
        assert depth == 5

    def test_get_stats(self):
        monitor = QueueDepthMonitor()
        monitor.register_queue("test_queue")
        monitor.record("test_queue", 10)
        stats = monitor.get_stats("test_queue")
        assert stats["current"] == 10
        assert stats["max"] == 10

    def test_get_alerts(self):
        monitor = QueueDepthMonitor(alert_threshold=5)
        monitor.register_queue("test_queue")
        monitor.record("test_queue", 10)
        alerts = monitor.get_alerts()
        assert len(alerts) == 1


class TestBackpressureHandler:
    @pytest.mark.asyncio
    async def test_execute(self):
        handler = BackpressureHandler(max_concurrency=2)
        result = await handler.execute(lambda: 42)
        assert result == 42

    @pytest.mark.asyncio
    async def test_execute_stream(self):
        handler = BackpressureHandler(max_concurrency=2, queue_size=10)
        async def items():
            for i in range(3):
                yield i
        results = []
        async for result in handler.execute_stream(items(), lambda x: x * 2):
            results.append(result)
        assert len(results) == 3


class TestBatchProcessor:
    @pytest.mark.asyncio
    async def test_process_async(self):
        processor = BatchProcessor(batch_size=2, max_workers=2)
        items = [1, 2, 3, 4]
        result = await processor.process_async(items, lambda x: x * 2)
        assert result.total == 4
        assert result.successful == 4
        assert len(result.results) == 4

    @pytest.mark.asyncio
    async def test_process_stream_async(self):
        processor = BatchProcessor(batch_size=2, max_workers=2)
        items = [1, 2, 3]
        results = await processor.process_stream_async(items, lambda x: x * 2)
        assert len(results) == 3


class TestLazyLoader:
    def test_get(self):
        state = {"count": 0}
        def factory():
            state["count"] += 1
            return "value"
        loader = LazyLoader(factory, cache=True)
        assert loader.get() == "value"
        assert loader.get() == "value"
        assert loader.load_count == 1

    def test_invalidate(self):
        state = {"count": 0}
        def factory():
            state["count"] += 1
            return "value"
        loader = LazyLoader(factory, cache=True)
        loader.get()
        loader.invalidate()
        loader.get()
        assert loader.load_count == 2

    @pytest.mark.asyncio
    async def test_get_async(self):
        state = {"count": 0}
        async def factory():
            state["count"] += 1
            return "value"
        loader = LazyLoader(factory, cache=True)
        result = await loader.get_async()
        assert result == "value"
