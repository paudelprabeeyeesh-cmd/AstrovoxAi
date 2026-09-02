"""Tests for the Distributed AIOS layer (Stage 32)."""

from __future__ import annotations

import asyncio
import os
import unittest

from app.aios.consensus import (
    ConfigurationStore,
    ConsensusLayer,
    DistributedLock,
    Node,
    get_consensus,
)
from app.aios.healing import (
    CircuitBreaker,
    CircuitRegistry,
    HealthProbe,
    RetryPolicy,
    Retrier,
    get_self_healing,
)
from app.aios.memory import (
    ColdStore,
    HotStore,
    MemoryManager,
    MemoryTier,
    VectorIndex,
    WarmStore,
    get_memory_manager,
)
from app.aios.mesh import (
    HealthCheck,
    ServiceInstance,
    ServiceRegistry,
    ServiceState,
    get_service_registry,
    seed_default_services,
)
from app.aios.observability import (
    Observability,
    SLO,
    get_aios_observability,
)
from app.aios.resources import ResourceManager, ResourceUsage, get_resource_manager
from app.aios.runtime import (
    AgentQuota,
    AIRuntime,
    Message,
    MessageRouter,
    QuotaUsage,
    get_ai_runtime,
)
from app.aios.scheduler import (
    DistributedQueue,
    DistributedScheduler,
    Job,
    JobState,
    LeaderElector,
    Worker,
    get_distributed_scheduler,
)
from app.aios.search import (
    LexicalIndex,
    SearchDocument,
    SearchModality,
    UniversalSearch,
    get_universal_search,
)
from app.aios.security import (
    AuditLogger,
    Policy,
    PolicyAction,
    PolicyEngine,
    SecretManager,
    SecurityContext,
    SecurityLayer,
    get_security_layer,
)


# ---------------------------------------------------------------------------
# Service mesh
# ---------------------------------------------------------------------------


class ServiceMeshTest(unittest.TestCase):
    def test_register_and_discover(self):
        reg = ServiceRegistry()
        reg.register(ServiceInstance(id="", name="chat", version="1.0", host="h", port=80))
        reg.register(ServiceInstance(id="", name="chat", version="1.0", host="h", port=81))
        items = reg.discover("chat")
        self.assertEqual(len(items), 2)

    def test_pick_weighted(self):
        reg = ServiceRegistry()
        a = reg.register(ServiceInstance(id="a", name="chat", version="1.0", host="h", port=80, weight=10))
        b = reg.register(ServiceInstance(id="b", name="chat", version="1.0", host="h", port=81, weight=90))
        picked = reg.pick("chat")
        self.assertIsNotNone(picked)

    def test_unhealthy_excluded(self):
        reg = ServiceRegistry()
        inst = reg.register(ServiceInstance(id="", name="x", version="1", host="h", port=80))
        inst.state = ServiceState.UNHEALTHY
        self.assertEqual(reg.discover("x"), [])

    def test_evict_stale(self):
        reg = ServiceRegistry()
        inst = reg.register(ServiceInstance(id="", name="x", version="1", host="h", port=80))
        inst.last_heartbeat = 0
        self.assertEqual(len(reg.evict_stale(timeout=1)), 1)

    def test_seed(self):
        seed_default_services()
        self.assertGreaterEqual(len(get_service_registry().list()), 10)


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------


class MemoryTest(unittest.TestCase):
    def test_hot_put_get(self):
        store = HotStore()
        store.put("k", "v", ttl=10)
        self.assertEqual(store.get("k").value, "v")

    def test_ttl_expiry(self):
        store = HotStore()
        import time
        store.put("k", "v", ttl=0.0)
        time.sleep(0.05)
        self.assertIsNone(store.get("k"))

    def test_warm_replicas(self):
        store = WarmStore()
        from app.aios.memory import MemoryRecord
        rec = MemoryRecord(key="k", value="v", tier=MemoryTier.WARM)
        store.put(rec, replicas=2)
        self.assertEqual(len(store.replicas("k")), 2)

    def test_cold_compress(self):
        store = ColdStore()
        blob_id = store.put("k", "hello world" * 50, compress=True)
        self.assertIsNotNone(blob_id)
        self.assertEqual(store.get("k"), b"hello world" * 50)

    def test_vector_search(self):
        idx = VectorIndex()
        idx.upsert("a", [1.0, 0.0, 0.0])
        idx.upsert("b", [0.0, 1.0, 0.0])
        idx.upsert("c", [0.9, 0.1, 0.0])
        hits = idx.search([1.0, 0.0, 0.0], top_k=2)
        self.assertEqual(hits[0][0], "a")

    def test_memory_manager_dedup(self):
        mm = MemoryManager()
        r1 = mm.put("k1", "hello")
        r2 = mm.put("k2", "hello")  # same value -> dedup
        self.assertEqual(r1.key, r2.key)
        self.assertGreaterEqual(r2.version, 1)

    def test_promote(self):
        mm = MemoryManager()
        mm.put("k", "v", tier=MemoryTier.HOT)
        promoted = mm.promote("k", MemoryTier.WARM)
        self.assertEqual(promoted.tier, MemoryTier.WARM)


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------


async def _ok(job: Job) -> dict:
    return {"ok": True, "job": job.name}


async def _fail(job: Job) -> dict:
    raise RuntimeError("nope")


class DistributedSchedulerTest(unittest.TestCase):
    def test_leader_election(self):
        elector = LeaderElector(ttl=2.0)
        self.assertTrue(elector.try_become_leader("node-a"))
        self.assertFalse(elector.try_become_leader("node-b"))
        self.assertEqual(elector.leader(), "node-a")
        elector.step_down()
        self.assertTrue(elector.try_become_leader("node-b"))

    def test_work_stealing(self):
        sched = DistributedScheduler(max_workers=2)
        sched.submit(Job(id="a", name="a", handler=_ok, priority=5))
        sched.submit(Job(id="b", name="b", handler=_ok, priority=10))
        result = asyncio.run(sched.run(deadline_s=2.0))
        self.assertTrue(result["ok"])

    def test_retry_then_fail(self):
        sched = DistributedScheduler(max_workers=1)
        sched.submit(Job(id="a", name="a", handler=_fail, max_retries=2, timeout_seconds=1.0))
        result = asyncio.run(sched.run(deadline_s=5.0))
        self.assertFalse(result["ok"])

    def test_dependency_chain(self):
        sched = DistributedScheduler(max_workers=2)
        sched.submit(Job(id="a", name="a", handler=_ok))
        sched.submit(Job(id="b", name="b", depends_on=["a"], handler=_ok))
        sched.submit(Job(id="c", name="c", depends_on=["b"], handler=_ok))
        result = asyncio.run(sched.run(deadline_s=3.0))
        self.assertEqual(result["succeeded"], 3)

    def test_worker_runs_job(self):
        sched = DistributedScheduler(max_workers=1)
        sched.submit(Job(id="x", name="x", handler=_ok))
        result = asyncio.run(sched.run(deadline_s=1.0))
        self.assertTrue(result["ok"])


# ---------------------------------------------------------------------------
# AI runtime
# ---------------------------------------------------------------------------


class AIRuntimeTest(unittest.TestCase):
    def test_register_and_run(self):
        runtime = AIRuntime()
        runtime.register_agent("planner", "planner", max_concurrent=2)
        result = asyncio.run(runtime.run_agent("planner", "solve X"))
        self.assertTrue(result["ok"])
        self.assertEqual(result["agent"], "planner")

    def test_quota_exceeded(self):
        runtime = AIRuntime()
        quota = AgentQuota(name="a", max_concurrent=1, max_tasks_per_minute=1)
        # First acquire succeeds
        self.assertEqual(quota.acquire(), QuotaUsage.OK)
        # Second exceeds
        self.assertEqual(quota.acquire(), QuotaUsage.EXCEEDED)
        quota.release()

    def test_messaging(self):
        router = MessageRouter()
        router.register("alice")
        router.register("bob")
        msg = router.send("alice", "bob", "task", {"x": 1})
        self.assertEqual(len(router.inbox("bob")), 1)
        self.assertEqual(router.inbox("bob")[0].id, msg.id)

    def test_delegation(self):
        runtime = AIRuntime()
        runtime.register_agent("planner", "planner")
        runtime.register_agent("executor", "executor")
        req = asyncio.run(runtime.delegate("planner", "executor", "do X"))
        self.assertEqual(req.state, "succeeded")


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


class UniversalSearchTest(unittest.TestCase):
    def test_index_and_search(self):
        search = UniversalSearch()
        search.index(SearchDocument(id="1", modality=SearchModality.DOCUMENT, title="a", content="the quick brown fox"))
        search.index(SearchDocument(id="2", modality=SearchModality.DOCUMENT, title="b", content="lazy dog sleeps"))
        hits = search.search("quick fox")
        self.assertGreater(len(hits), 0)
        self.assertEqual(hits[0].doc.id, "1")

    def test_hybrid_ranking(self):
        search = UniversalSearch()
        search.index(
            SearchDocument(
                id="1",
                modality=SearchModality.DOCUMENT,
                title="alpha",
                content="machine learning",
                embedding=[1.0, 0.0, 0.0],
            )
        )
        search.index(
            SearchDocument(
                id="2",
                modality=SearchModality.DOCUMENT,
                title="beta",
                content="deep learning",
                embedding=[0.0, 1.0, 0.0],
            )
        )
        hits = search.search("learning", embedding=[1.0, 0.0, 0.0])
        self.assertGreater(len(hits), 0)

    def test_modality_filter(self):
        search = UniversalSearch()
        search.index(SearchDocument(id="1", modality=SearchModality.IMAGE, title="x", content="cat picture"))
        search.index(SearchDocument(id="2", modality=SearchModality.DOCUMENT, title="y", content="cat document"))
        hits = search.search("cat", modalities=[SearchModality.DOCUMENT])
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].doc.id, "2")

    def test_personalization(self):
        search = UniversalSearch()
        search.index(SearchDocument(id="1", modality=SearchModality.DOCUMENT, title="x", content="foo bar"))
        search.index(SearchDocument(id="2", modality=SearchModality.DOCUMENT, title="y", content="foo baz"))
        search.record_interaction("user1", "1")
        hits = search.search("foo", user_id="user1", personalization_weight=1.0)
        self.assertEqual(hits[0].doc.id, "1")


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


class ResourceManagerTest(unittest.TestCase):
    def test_record_and_snapshot(self):
        rm = ResourceManager()
        for i in range(5):
            rm.record(ResourceUsage(cpu=0.5 + i * 0.05, memory=0.4, gpu=0.2))
        snap = rm.snapshot()
        self.assertIsNotNone(snap["latest"])
        self.assertEqual(snap["history"][-1]["cpu"], round(0.5 + 4 * 0.05, 4))

    def test_predict_trend(self):
        rm = ResourceManager()
        for i in range(5):
            rm.record(ResourceUsage(cpu=0.1 + i * 0.1))
        pred = rm.predict("cpu", horizon_s=10.0)
        self.assertIsNotNone(pred)
        self.assertGreater(pred, 0.5)

    def test_recommend_replicas(self):
        rm = ResourceManager()
        for i in range(5):
            rm.record(ResourceUsage(cpu=0.95))
        rec = rm.recommend_replicas("chat")
        self.assertGreaterEqual(rec, 2)

    def test_cost_projection(self):
        rm = ResourceManager()
        proj = rm.cost_projection(hourly_token_rate=100_000)
        self.assertGreater(proj["monthly"], 0)


# ---------------------------------------------------------------------------
# Consensus
# ---------------------------------------------------------------------------


class ConsensusTest(unittest.TestCase):
    def test_distributed_lock(self):
        lock = DistributedLock()
        self.assertTrue(lock.acquire("k", "node1", ttl=5))
        self.assertFalse(lock.acquire("k", "node2", ttl=5))
        self.assertTrue(lock.renew("k", "node1", ttl=5))
        self.assertTrue(lock.release("k", "node1"))
        self.assertTrue(lock.acquire("k", "node2", ttl=5))

    def test_cluster_membership(self):
        from app.aios.consensus import ClusterMembership
        cm = ClusterMembership(gossip_interval_s=0.1)
        cm.add(Node(id="n1", address="a"))
        cm.add(Node(id="n2", address="b"))
        cm.sweep()
        self.assertEqual(len(cm.nodes(only_healthy=True)), 2)

    def test_quorum(self):
        from app.aios.consensus import ClusterMembership
        cm = ClusterMembership()
        self.assertTrue(cm.quorum(3))
        self.assertFalse(cm.quorum(1, failures=1))

    def test_configuration_store(self):
        store = ConfigurationStore()
        v1 = store.set("key", "v1")
        v2 = store.set("key", "v2")
        self.assertEqual(v1, 1)
        self.assertEqual(v2, 2)
        self.assertEqual(store.get("key"), "v2")
        self.assertEqual(store.version("key"), 2)

    def test_consensus_facade(self):
        consensus = ConsensusLayer()
        self.assertIn("membership", consensus.status())


# ---------------------------------------------------------------------------
# Self-healing
# ---------------------------------------------------------------------------


class SelfHealingTest(unittest.TestCase):
    def test_circuit_opens_after_failures(self):
        breaker = CircuitBreaker(name="x", failure_threshold=2, reset_timeout_s=0.1)
        self.assertTrue(breaker.allow())
        breaker.record_failure()
        self.assertTrue(breaker.allow())
        breaker.record_failure()
        self.assertFalse(breaker.allow())
        # Reset timeout must pass before half-open is allowed.
        self.assertFalse(breaker.allow())  # still open

    def test_circuit_half_open_after_timeout(self):
        breaker = CircuitBreaker(name="y", failure_threshold=1, reset_timeout_s=0.05)
        breaker.record_failure()
        self.assertFalse(breaker.allow())
        import time
        time.sleep(0.06)
        self.assertTrue(breaker.allow())  # transitions to half-open

    def test_retry_policy(self):
        policy = RetryPolicy(max_attempts=3, base_delay_s=0.0, max_delay_s=0.0)
        self.assertEqual(policy.delay(0), 0.0)
        self.assertGreater(policy.delay(2), 0.0)

    def test_retrier_eventually_succeeds(self):
        reg = CircuitRegistry()
        retrier = Retrier(reg, RetryPolicy(max_attempts=3, base_delay_s=0.0, max_delay_s=0.0))
        calls = {"n": 0}

        async def flaky():
            calls["n"] += 1
            if calls["n"] < 2:
                raise RuntimeError("nope")
            return {"ok": True}

        result = asyncio.run(retrier.run("flaky", flaky))
        self.assertTrue(result["ok"])
        self.assertEqual(calls["n"], 2)

    def test_self_healing_recover(self):
        sh = get_self_healing()
        action = sh.recover("svc", "restart", "test")
        self.assertEqual(action.status, "completed")
        self.assertGreater(len(sh.actions), 0)


# ---------------------------------------------------------------------------
# Observability
# ---------------------------------------------------------------------------


class ObservabilityTest(unittest.TestCase):
    def test_slo_compliance(self):
        obs = Observability()
        for v in [10, 20, 9000, 30]:
            obs.record_slo("latency_p95_ms", v)
        status = obs.slo_status()
        latency = next(s for s in status if s["name"] == "latency_p95_ms")
        self.assertLess(latency["compliance"], 1.0)

    def test_dependency_map(self):
        obs = get_aios_observability()
        obs.dependencies.record("chat", "memory")
        obs.dependencies.record("chat", "search")
        deps = obs.dependencies.to_dict()
        self.assertGreaterEqual(deps["services"], 2)

    def test_logs_search(self):
        obs = Observability()
        obs.logs.info("chat", "started")
        obs.logs.warn("chat", "slow")
        logs = obs.logs.search(service="chat")
        self.assertEqual(len(logs), 2)

    def test_traces(self):
        obs = Observability()
        trace = obs.traces.start("test", request_id="r1")
        obs.traces.record_span(trace, {"name": "step1", "duration_ms": 5.0})
        obs.traces.end(trace)
        recent = obs.traces.recent(limit=10)
        self.assertGreaterEqual(len(recent), 1)


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------


class SecurityTest(unittest.TestCase):
    def test_policy_allow(self):
        engine = PolicyEngine()
        engine.add(Policy(name="a", effect=PolicyAction.ALLOW, actions=["read"], resources=["x"]))
        self.assertEqual(engine.evaluate(principal="u", action="read", resource="x"), PolicyAction.ALLOW)
        self.assertEqual(engine.evaluate(principal="u", action="delete", resource="x"), PolicyAction.DENY)

    def test_policy_with_conditions(self):
        engine = PolicyEngine()
        engine.add(
            Policy(
                name="ws",
                effect=PolicyAction.ALLOW,
                actions=["*"],
                resources=["*"],
                conditions={"workspace": "w1"},
            )
        )
        self.assertEqual(
            engine.evaluate(principal="u", action="read", resource="x", context={"workspace": "w1"}),
            PolicyAction.ALLOW,
        )
        self.assertEqual(
            engine.evaluate(principal="u", action="read", resource="x", context={"workspace": "w2"}),
            PolicyAction.DENY,
        )

    def test_secret_manager_roundtrip(self):
        sm = SecretManager()
        sm.put("api", "sk-1234567890")
        self.assertEqual(sm.get("api"), "sk-1234567890")
        v = sm.rotate("api", "sk-9999")
        self.assertEqual(v, "v2")
        self.assertEqual(sm.get("api"), "sk-9999")

    def test_audit_logger_verifies(self):
        log = AuditLogger()
        log.record("user", "login", "system")
        log.record("user", "fetch", "doc", outcome="denied")
        self.assertTrue(log.verify())
        # Tamper
        log._entries[0]["actor"] = "evil"
        self.assertFalse(log.verify())

    def test_security_context(self):
        ctx = SecurityContext("u1", ["read", "write"], mTLS=True)
        self.assertTrue(ctx.has_scope("read"))
        self.assertFalse(ctx.has_scope("admin"))

    def test_security_layer_authorize(self):
        layer = SecurityLayer()
        ctx = SecurityContext("admin", ["*"], mTLS=True)
        self.assertEqual(
            layer.authorize(ctx, "delete", "user/1"),
            PolicyAction.ALLOW,
        )
        ctx2 = SecurityContext("user", ["read"])
        self.assertEqual(
            layer.authorize(ctx2, "delete", "user/1"),
            PolicyAction.DENY,
        )
        self.assertGreater(len(layer.audit.list()), 0)


if __name__ == "__main__":
    unittest.main()