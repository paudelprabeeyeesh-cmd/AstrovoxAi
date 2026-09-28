"""Test suite for distributed GPU scheduler."""

import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest

from models.llm.scheduler.api import app
from models.llm.scheduler.elastic import (
    CostOptimizer,
    ElasticScaler,
    InstancePricing,
    ScalingPolicy,
    ScalingPolicyConfig,
)
from models.llm.scheduler.failover import (
    FailoverManager,
    HealthCheckResult,
    HealthChecker,
    HealthStatus,
    RecoveryStrategy,
)
from models.llm.scheduler.gpu import (
    GPUNode,
    GPUPool,
    GPUResourceError,
    GPUStats,
)
from models.llm.scheduler.queue import (
    FairShareScheduler,
    Job,
    JobPriority,
    JobQueue,
    JobStatus,
    PreemptionPolicy,
    TenantQuota,
)


# ---------------------------------------------------------------------------
# GPU tests
# ---------------------------------------------------------------------------
class TestGPUNode:
    def test_memory_free(self):
        node = GPUNode(node_id="n1", memory_total_mb=1024, gpu_type="a100")
        assert node.memory_free_mb == 1024
        node.stats.memory_used_mb = 400
        assert node.memory_free_mb == 624

    def test_can_fit(self):
        node = GPUNode(node_id="n1", memory_total_mb=1024, gpu_type="a100")
        assert node.can_fit(512) is True
        assert node.can_fit(2048) is False

    def test_health_from_temperature(self):
        node = GPUNode(node_id="n1", memory_total_mb=1024, gpu_type="a100")
        node.update_stats(GPUStats(temperature_c=90.0))
        assert node.health == HealthStatus.HEALTHY
        node.update_stats(GPUStats(temperature_c=98.0))
        assert node.health == HealthStatus.DEGRADED
        node.update_stats(GPUStats(temperature_c=106.0))
        assert node.health == HealthStatus.UNHEALTHY

    def test_assign_and_release_job(self):
        node = GPUNode(node_id="n1", memory_total_mb=1024, gpu_type="a100")
        node.assign_job("job-1")
        assert "job-1" in node.running_jobs
        with pytest.raises(GPUResourceError):
            node.assign_job("job-1")
        node.release_job("job-1")
        assert "job-1" not in node.running_jobs

    def test_node_id_generated(self):
        node = GPUNode(node_id="", memory_total_mb=1024, gpu_type="a100")
        assert node.node_id


class TestGPUPool:
    def test_add_and_get(self):
        pool = GPUPool()
        node = GPUNode(node_id="n1", memory_total_mb=4096, gpu_type="h100")
        pool.add_node(node)
        assert len(pool) == 1
        assert pool.get_node("n1") is node

    def test_remove_node(self):
        pool = GPUPool()
        node = GPUNode(node_id="n1", memory_total_mb=4096, gpu_type="h100")
        pool.add_node(node)
        node.assign_job("job-1")
        pool.remove_node("n1")
        assert len(pool) == 0
        assert "job-1" not in node.running_jobs

    def test_find_available(self):
        pool = GPUPool()
        pool.add_node(GPUNode(node_id="n1", memory_total_mb=2048, gpu_type="a100"))
        pool.add_node(GPUNode(node_id="n2", memory_total_mb=2048, gpu_type="a100"))
        pool.add_node(GPUNode(node_id="n3", memory_total_mb=2048, gpu_type="v100"))
        pool.update_node_stats("n1", GPUStats(memory_used_mb=0))
        pool.update_node_stats("n2", GPUStats(memory_used_mb=1900))
        results = pool.find_available(128, gpu_type="a100")
        assert [n.node_id for n in results] == ["n1", "n2"]

    def test_best_fit(self):
        pool = GPUPool()
        pool.add_node(GPUNode(node_id="n1", memory_total_mb=4096, gpu_type="a100"))
        pool.add_node(GPUNode(node_id="n2", memory_total_mb=8192, gpu_type="a100"))
        pool.update_node_stats("n1", GPUStats(memory_used_mb=0))
        pool.update_node_stats("n2", GPUStats(memory_used_mb=0))
        node = pool.best_fit(1024, gpu_type="a100")
        assert node is not None
        assert node.node_id == "n1"

    def test_totals(self):
        pool = GPUPool()
        pool.add_node(GPUNode(node_id="n1", memory_total_mb=2048, gpu_type="a100"))
        pool.add_node(GPUNode(node_id="n2", memory_total_mb=4096, gpu_type="a100"))
        pool.update_node_stats("n1", GPUStats(memory_used_mb=0))
        pool.update_node_stats("n2", GPUStats(memory_used_mb=0))
        assert pool.total_memory_mb() == 6144
        assert pool.total_free_memory_mb() == 6144


# ---------------------------------------------------------------------------
# Queue tests
# ---------------------------------------------------------------------------
class TestJobQueue:
    def test_enqueue_dequeue(self):
        q = JobQueue()
        job = q.enqueue(Job(name="j1"))
        assert job.status == JobStatus.QUEUED
        job2 = q.dequeue()
        assert job2 is job

    def test_get_and_remove(self):
        q = JobQueue()
        job = q.enqueue(Job(name="j1"))
        assert q.get(job.job_id) is job
        removed = q.remove(job.job_id)
        assert removed is job
        assert q.get(job.job_id) is None

    def test_update_status(self):
        q = JobQueue()
        job = q.enqueue(Job(name="j1"))
        updated = q.update_status(job.job_id, JobStatus.RUNNING)
        assert updated.status == JobStatus.RUNNING
        assert updated.started_at is not None

    def test_pending_and_running(self):
        q = JobQueue()
        j1 = q.enqueue(Job(name="j1"))
        j2 = q.enqueue(Job(name="j2"))
        q.update_status(j1.job_id, JobStatus.RUNNING)
        assert len(q.pending_jobs()) == 1
        assert len(q.running_jobs()) == 1


class TestFairShareScheduler:
    def test_can_schedule_within_quota(self):
        q = JobQueue()
        s = FairShareScheduler(q, TenantQuota(tenant_id="t1", max_parallel_jobs=2))
        j1 = q.enqueue(Job(tenant_id="t1"))
        j2 = q.enqueue(Job(tenant_id="t1"))
        assert s.can_schedule(j1) is True
        s.record_scheduled(j1)
        assert s.can_schedule(j2) is True
        s.record_scheduled(j2)
        j3 = Job(tenant_id="t1")
        assert s.can_schedule(j3) is False

    def test_next_queued_skips_full_tenant(self):
        q = JobQueue()
        quota = TenantQuota(tenant_id="t1", max_parallel_jobs=1)
        s = FairShareScheduler(q, default_quota=quota)
        j1 = q.enqueue(Job(tenant_id="t1"))
        j2 = q.enqueue(Job(tenant_id="t2"))
        s.record_scheduled(j1)
        next_job = s.next_queued()
        assert next_job is j2

    def test_preemptible_selection(self):
        q = JobQueue()
        s = FairShareScheduler(q)
        j1 = q.enqueue(Job(name="low", priority=JobPriority.LOW, preemptible=True))
        q.update_status(j1.job_id, JobStatus.RUNNING)
        victims = s.preemptible_jobs(PreemptionPolicy.LOWEST_PRIORITY_FIRST, 1)
        assert victims == [j1]


# ---------------------------------------------------------------------------
# Failover tests
# ---------------------------------------------------------------------------
class TestHealthChecker:
    def test_register_and_check(self):
        hc = HealthChecker(check_interval_seconds=1.0)
        hc.register_check("n1", lambda: HealthCheckResult(node_id="n1", status=HealthStatus.HEALTHY))
        result = hc.run_check("n1")
        assert result.status == HealthStatus.HEALTHY
        assert result.latency_ms >= 0

    def test_unhealthy_nodes(self):
        hc = HealthChecker(check_interval_seconds=1.0)
        hc._results["n1"] = HealthCheckResult(node_id="n1", status=HealthStatus.UNHEALTHY)
        hc._results["n2"] = HealthCheckResult(node_id="n2", status=HealthStatus.HEALTHY)
        assert hc.unhealthy_nodes() == ["n1"]


class TestFailoverManager:
    def test_handle_failure(self):
        fm = FailoverManager(recovery_strategy=RecoveryStrategy.RESCHEDULE, max_retries=3)
        action = fm.handle_failure("n1", "job-1")
        assert action == "reschedule"

    def test_recover_job(self):
        fm = FailoverManager()
        action = fm.recover_job("job-1", "n1")
        assert action == "rescheduled"

    def test_escalation(self):
        fm = FailoverManager(max_retries=1)
        fm.handle_failure("n1")
        action = fm.handle_failure("n1")
        assert action == "escalated"

    def test_callback_on_failover(self):
        fm = FailoverManager()
        events = []
        fm.on_failover("n1", lambda job_id: events.append(job_id))
        fm.handle_failure("n1", "job-1")
        assert events == ["job-1"]


# ---------------------------------------------------------------------------
# Elastic tests
# ---------------------------------------------------------------------------
class TestCostOptimizer:
    def test_select_instance_within_budget(self):
        opt = CostOptimizer(
            pricing=[
                InstancePricing(instance_type="gpu-small", price_per_hour_usd=1.0),
                InstancePricing(instance_type="gpu-large", price_per_hour_usd=10.0),
            ]
        )
        choice = opt.select_instance(required_memory_mb=1024, budget_per_hour_usd=2.0)
        assert choice is not None
        assert choice.instance_type == "gpu-small"

    def test_select_instance_none(self):
        opt = CostOptimizer(
            pricing=[InstancePricing(instance_type="gpu-large", price_per_hour_usd=10.0)]
        )
        choice = opt.select_instance(required_memory_mb=1024, budget_per_hour_usd=2.0)
        assert choice is None

    def test_estimate_cost(self):
        opt = CostOptimizer(
            pricing=[InstancePricing(instance_type="gpu-small", price_per_hour_usd=1.0)]
        )
        assert opt.estimate_cost("gpu-small", 2.0) == pytest.approx(1.4)

    def test_recommend_scale_up(self):
        opt = CostOptimizer()
        result = opt.recommend_scale(current_nodes=1, queue_depth=4, avg_runtime_seconds=60.0)
        assert result["action"] == "scale_up"

    def test_recommend_scale_down(self):
        opt = CostOptimizer()
        result = opt.recommend_scale(current_nodes=4, queue_depth=0, avg_runtime_seconds=60.0)
        assert result["action"] == "scale_down"


class TestElasticScaler:
    def test_evaluate_scale_up(self):
        scaler = ElasticScaler(ScalingPolicyConfig(min_nodes=1, max_nodes=5))
        result = scaler.evaluate({"queue_depth": 10})
        assert result["action"] == "scale_up"

    def test_evaluate_scale_down(self):
        scaler = ElasticScaler(ScalingPolicyConfig(min_nodes=1, max_nodes=5))
        scaler.set_nodes(2)
        result = scaler.evaluate({"queue_depth": 0})
        assert result["action"] == "scale_down"

    def test_cool_down(self):
        scaler = ElasticScaler(ScalingPolicyConfig(cool_down_seconds=60.0))
        scaler.evaluate({"queue_depth": 10})
        result = scaler.evaluate({"queue_depth": 0})
        assert result["action"] == "cool_down"

    def test_set_nodes_bounds(self):
        scaler = ElasticScaler(ScalingPolicyConfig(min_nodes=1, max_nodes=5))
        scaler.set_nodes(10)
        assert scaler.current_nodes() == 5
        scaler.set_nodes(0)
        assert scaler.current_nodes() == 1


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------
class TestSchedulerAPI:
    @pytest.fixture(autouse=True)
    def _setup(self):
        from fastapi.testclient import TestClient

        self.client = TestClient(app)

    def test_submit_and_get_job(self):
        resp = self.client.post("/jobs", json={"name": "test-job", "required_gpus": 1})
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]
        resp = self.client.get(f"/jobs/{job_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "test-job"

    def test_cancel_job(self):
        resp = self.client.post("/jobs", json={"name": "to-cancel", "required_gpus": 1})
        job_id = resp.json()["job_id"]
        resp = self.client.delete(f"/jobs/{job_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == JobStatus.CANCELLED.value

    def test_list_jobs_with_filter(self):
        resp = self.client.post("/jobs", json={"name": "filtered", "tenant_id": "t1", "required_gpus": 1})
        job_id = resp.json()["job_id"]
        resp = self.client.get("/jobs", params={"tenant_id": "t1"})
        assert resp.status_code == 200
        assert any(j["job_id"] == job_id for j in resp.json())

    def test_register_and_list_gpus(self):
        resp = self.client.post("/gpus", json={
            "node_id": "api-n1",
            "gpu_type": "a100",
            "memory_total_mb": 4096,
            "health": "healthy",
        })
        assert resp.status_code == 200
        resp = self.client.get("/gpus")
        assert resp.status_code == 200
        assert any(g["node_id"] == "api-n1" for g in resp.json())

    def test_get_missing_job(self):
        resp = self.client.get("/jobs/missing-id")
        assert resp.status_code == 404

    def test_set_scaling_policy(self):
        resp = self.client.post("/scaling/policy", json={
            "policy": "cpu_utilization",
            "target_nodes": 3,
        })
        assert resp.status_code == 200
        assert resp.json()["policy"] == "cpu_utilization"

    def test_cost_estimate(self):
        resp = self.client.get("/cost/estimate", params={"instance_type": "gpu-small", "hours": 2.0})
        assert resp.status_code == 200
        assert "estimated_cost_usd" in resp.json()

    def test_cost_recommend(self):
        resp = self.client.post("/cost/recommend", json={
            "current_nodes": 1,
            "queue_depth": 4,
            "avg_runtime_seconds": 60.0,
        })
        assert resp.status_code == 200
        assert resp.json()["action"] == "scale_up"
