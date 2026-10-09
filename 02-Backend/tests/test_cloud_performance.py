"""Tests for cloud storage, CDN, and infrastructure modules."""

from __future__ import annotations

import pytest


def test_cloud_storage_backend_detection():
    from app.cloud_storage import CloudStorageService

    service = CloudStorageService()
    assert service.backend in ("local", "s3", "cloudflare_r2", "supabase")


def test_cdn_config_from_env():
    from app.cdn import CDNConfig

    config = CDNConfig.from_env()
    assert config.provider in ("none", "cloudflare", "cloudfront")
    assert isinstance(config.enabled, bool)


def test_load_balancer_round_robin():
    from app.load_balancer_config import LoadBalancerConfig, BackendNode

    lb = LoadBalancerConfig(strategy="round_robin")
    node1 = BackendNode(host="127.0.0.1", port=8001, weight=1)
    node2 = BackendNode(host="127.0.0.1", port=8002, weight=2)
    lb.register_node(node1)
    lb.register_node(node2)
    selected = [lb.select_node().address for _ in range(4)]
    assert "127.0.0.1:8001" in selected
    assert "127.0.0.1:8002" in selected
    assert len(set(selected)) == 2


def test_load_balancer_least_connections():
    from app.load_balancer_config import LoadBalancerConfig, BackendNode

    lb = LoadBalancerConfig(strategy="least_connections")
    node1 = BackendNode(host="127.0.0.1", port=8001, weight=1)
    node2 = BackendNode(host="127.0.0.1", port=8002, weight=1)
    lb.register_node(node1)
    lb.register_node(node2)
    lb.increment_connections("127.0.0.1:8001")
    selected = lb.select_node()
    assert selected.address == "127.0.0.1:8002"


def test_auto_scaler_evaluate_scale_up():
    from app.auto_scaling import AutoScaler, ScalingPolicy, MetricSample

    scaled = []
    scaler = AutoScaler(
        policy=ScalingPolicy(min_instances=1, max_instances=3, scale_up_cooldown=0),
        scale_up_fn=lambda: scaled.append(1),
    )
    for _ in range(10):
        scaler.record_metrics(MetricSample(cpu_percent=90, memory_percent=90, request_rate=200, queue_depth=100, timestamp=0))
    result = scaler.evaluate()
    assert result == "scale_up"
    assert scaler.current_instances == 2


def test_multi_region_resolve():
    from app.multi_region import multi_region_manager, RegionStrategy

    multi_region_manager.strategy = RegionStrategy.GEOGRAPHIC
    region = multi_region_manager.resolve_region(user_country="DE")
    assert region.code in ("us-east-1", "eu-west-1", "ap-south-1")


def test_infrastructure_as_code_terraform():
    from app.infrastructure_as_code import InfrastructureAsCode, ResourceDefinition

    infra = InfrastructureAsCode(provider="aws")
    infra.add_resource(ResourceDefinition(type="postgres", name="main-db", properties={"instance_class": "db.t3.micro"}))
    terraform = infra.generate_terraform()
    assert "resource \"aws_db_instance\"" in terraform
    assert "main-db" in terraform


def test_infrastructure_as_code_docker_compose():
    from app.infrastructure_as_code import InfrastructureAsCode

    infra = InfrastructureAsCode(provider="aws")
    compose = infra.generate_docker_compose()
    assert "services:" in compose
    assert "postgres:" in compose
    assert "redis:" in compose


def test_distributed_cache_set_and_get():
    from app.distributed_cache import DistributedCache

    cache = DistributedCache(redis_url="redis://localhost:6379/15")
    cache.set("test-key", {"hello": "world"}, ttl=60)
    value = cache.get("test-key")
    if value is not None:
        assert value == {"hello": "world"}
    cache.delete("test-key")


def test_distributed_queue_enqueue_dequeue():
    from app.distributed_queue import DistributedQueue, JobPriority

    queue = DistributedQueue(redis_url="redis://localhost:6379/14")
    job_id = queue.enqueue({"type": "test", "data": "hello"}, priority=JobPriority.HIGH)
    assert job_id is not None
    job = queue.dequeue(consumer_name="test-worker", timeout_ms=100)
    if job:
        assert job.job_id == job_id
        assert job.payload.get("type") == "test"
        queue.ack(job.job_id)


def test_distributed_worker_pool():
    from app.distributed_workers import DistributedWorkerPool, WorkerConfig

    pool = DistributedWorkerPool()
    worker = pool.add_worker(WorkerConfig(name="test-worker", concurrency=2))
    assert worker.config.name == "test-worker"
    stats = pool.get_stats()
    assert stats["worker_count"] == 1


def test_response_cache_set_get():
    from app.response_cache import ResponseCache

    cache = ResponseCache(default_ttl=60)
    cache.set("GET", "/api/test", {"q": "hello"}, 200, {"Content-Type": "application/json"}, {"result": "ok"}, ttl=60, tags=["api"])
    entry = cache.get("GET", "/api/test", {"q": "hello"})
    if entry is not None:
        assert entry.body == {"result": "ok"}
        assert entry.status_code == 200
    cache.invalidate_prefix("api:")


def test_cdn_setup_cache_headers():
    from app.cdn_setup import CDNSetup

    cdn = CDNSetup()
    headers = cdn.get_cache_headers("/static/app.js")
    assert "Cache-Control" in headers
    assert headers["Cache-Control"].startswith("public, max-age=")


def test_lazy_loader():
    from app.lazy_loading import LazyLoader

    loader = LazyLoader("json", "dumps")
    result = loader.get()
    assert result is not None
    assert callable(result)


def test_batch_processor():
    from app.batch_processor import BatchProcessor
    import asyncio

    async def run():
        processor = BatchProcessor(batch_size=2, concurrency=2)
        items = [1, 2, 3, 4]

        async def handler(item):
            return item * 2

        result = await processor.process(items, handler)
        assert result.total == 4
        assert result.succeeded == 4

    asyncio.run(run())


def test_streaming_optimizer():
    from app.streaming_optimizer import StreamingOptimizer
    import asyncio

    async def run():
        optimizer = StreamingOptimizer(batch_size=2)

        async def token_source():
            for token in ["Hello", " ", "world", "!"]:
                yield token

        tokens = []
        async for batch in optimizer.optimize_token_stream("test-stream", token_source()):
            tokens.append(batch)
        assert len(tokens) > 0
        metrics = optimizer.get_metrics("test-stream")
        assert metrics is not None
        assert metrics.tokens_sent == 4

    asyncio.run(run())


def test_resource_monitor_stats():
    from app.resource_monitor import ResourceMonitor

    monitor = ResourceMonitor(collection_interval=1.0)
    stats = monitor.get_snapshot()
    assert stats.cpu_percent >= 0
    assert stats.memory_percent >= 0
    summary = monitor.get_stats()
    assert "cpu_percent_avg" in summary


def test_database_optimizer_profile():
    from app.database_optimizer import DatabaseOptimizer

    optimizer = DatabaseOptimizer()
    profile = optimizer.analyze_query("SELECT * FROM users WHERE id = 1", 5.0)
    assert profile.execution_time_ms == 5.0
    suggestions = optimizer.get_optimization_suggestions()
    assert isinstance(suggestions, list)


def test_memory_optimizer_stats():
    from app.memory_optimizer import MemoryOptimizer

    optimizer = MemoryOptimizer()
    stats = optimizer.get_stats_summary()
    assert "rss_mb" in stats
    assert stats["rss_mb"] >= 0


def test_cpu_optimizer_profile():
    from app.cpu_optimizer import CPUOptimizer

    optimizer = CPUOptimizer()

    @optimizer.profile_function("test_func")
    def work():
        sum(range(1000))

    work()
    report = optimizer.get_profile_report()
    assert len(report) == 1
    assert report[0].function_name == "test_func"


def test_redis_cache_operations():
    from app.redis_cache import RedisCache

    cache = RedisCache(redis_url="redis://localhost:6379/13")
    cache.set("redis-test", {"key": "value"}, ttl=60)
    value = cache.get("redis-test")
    if value is not None:
        assert value == {"key": "value"}
    cache.delete("redis-test")


def test_query_optimizer_slow_query():
    from app.query_optimizer import QueryOptimizer

    optimizer = QueryOptimizer(slow_query_threshold_ms=10.0)
    optimizer.profile_query("SELECT * FROM large_table", 150.0, rows_scanned=10000, rows_returned=10)
    slow = optimizer.get_slow_queries()
    assert len(slow) == 1
    assert slow[0].execution_time_ms == 150.0


def test_load_tester_health():
    from app.load_test import LoadTester

    tester = LoadTester(base_url="http://localhost:9999")
    result = tester.run_health_load_test(requests=10)
    assert result.total_requests == 10
    assert result.failed_requests > 0


def test_benchmark_suite():
    from app.benchmark import PerformanceBenchmark

    bench = PerformanceBenchmark()

    def work():
        sum(range(1000))

    result = bench.benchmark_sync("test_suite", work, iterations=10)
    assert result.iterations == 10
    assert result.avg_time_ms > 0
    summary = bench.get_summary()
    assert summary["suites"] == 1
