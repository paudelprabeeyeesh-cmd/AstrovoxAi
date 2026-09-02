"""Tests for the Distributed Multimodal Intelligence Engine (Stage 31)."""

from __future__ import annotations

import asyncio
import os
import tempfile
import unittest

from app.kernel.agents import Agent, AgentRegistry, AgentSpec, get_agent_registry
from app.kernel.artifacts import (
    Artifact,
    ArtifactRegistry,
    ArtifactType,
    get_artifact_registry,
    make_text_artifact,
)
from app.kernel.bus import EventBus, get_event_bus
from app.kernel.context import (
    ContextBlock,
    ContextBudget,
    ContextEngine,
    ContextSection,
    TokenEstimator,
    history_source,
    instruction_source,
    memory_source,
    preferences_source,
    retrieval_source,
    system_source,
    tool_source,
)
from app.kernel.cost import CostManager, Quota, get_cost_manager
from app.kernel.evaluation import EvaluationStore, get_evaluation_store
from app.kernel.observability import (
    MetricsRegistry,
    Observability,
    SLODefinition,
    SLOTracker,
    Tracer,
    get_observability,
)
from app.kernel.router import (
    ModelCapability,
    ModelRegistry,
    ModelRouter,
    ModelSpec,
    RoutingPolicy,
    get_model_registry,
    get_model_router,
)
from app.kernel.scheduler import DAG, Job, WorkflowScheduler


class EventBusTest(unittest.TestCase):
    def test_subscribe_and_publish(self):
        bus = EventBus()
        received = []
        bus.subscribe("chat.created", lambda e: received.append(e.payload))
        bus.publish("chat.created", {"id": "1"})
        bus.publish("chat.created", {"id": "2"})
        self.assertEqual(len(received), 2)

    def test_wildcard(self):
        bus = EventBus()
        received = []
        bus.subscribe("*", lambda e: received.append(e.topic))
        bus.publish("a")
        bus.publish("b")
        self.assertIn("a", received)
        self.assertIn("b", received)

    def test_handler_error_isolated(self):
        bus = EventBus()
        bus.subscribe("x", lambda e: 1 / 0)
        good = []
        bus.subscribe("x", lambda e: good.append(e))
        bus.publish("x", {"y": 1})
        self.assertEqual(len(good), 1)


class ArtifactRegistryTest(unittest.TestCase):
    def test_register_and_derive(self):
        reg = ArtifactRegistry()
        a = make_text_artifact("hello", workspace_id="ws1", owner_id="u1")
        reg.register(a)
        b = reg.derive(a, type=ArtifactType.MEMORY, content="fact", metadata={})
        self.assertEqual(b.parent_id, a.id)
        self.assertEqual(b.version, 2)
        chain = reg.lineage(b.id)
        self.assertEqual(len(chain), 2)

    def test_filter_by_type_and_workspace(self):
        reg = ArtifactRegistry()
        reg.register(make_text_artifact("a", workspace_id="w1"))
        reg.register(make_text_artifact("b", workspace_id="w2"))
        self.assertEqual(len(reg.list(workspace_id="w1")), 1)
        self.assertEqual(len(reg.list(type=ArtifactType.TEXT)), 2)


class ContextEngineTest(unittest.TestCase):
    def test_dedup_and_rank(self):
        engine = ContextEngine()
        engine.register_source(system_source("system prompt"))
        engine.register_source(instruction_source("do X"))
        engine.register_source(retrieval_source([{"id": "1", "content": "doc1", "score": 2}]))
        blocks = engine.build({"request_id": "r"}, ContextBudget(max_tokens=1000))
        sections = [b.section for b in blocks]
        self.assertIn(ContextSection.SYSTEM, sections)
        self.assertIn(ContextSection.INSTRUCTIONS, sections)

    def test_budget_enforced(self):
        engine = ContextEngine(estimator=TokenEstimator())
        long = " ".join(["word"] * 200)
        engine.register_source(retrieval_source([{"id": "1", "content": long, "score": 1}]))
        blocks = engine.build({"request_id": "r"}, ContextBudget(max_tokens=20))
        self.assertLessEqual(sum(b.tokens for b in blocks), 20)

    def test_render(self):
        engine = ContextEngine()
        engine.register_source(system_source("be helpful"))
        blocks = engine.build({"request_id": "r"})
        rendered = engine.render(blocks)
        self.assertIn("be helpful", rendered)


class ModelRouterTest(unittest.TestCase):
    def test_decide(self):
        registry = get_model_registry()
        router = ModelRouter(registry)
        decision = router.decide(
            RoutingPolicy(min_quality=0.8, user_tier="authenticated"),
            1000,
            200,
        )
        self.assertIsNotNone(decision)
        self.assertGreater(decision.expected_cost, 0)
        self.assertGreater(len(decision.fallbacks), 0)

    def test_quality_filter(self):
        registry = ModelRegistry()
        registry.register(
            ModelSpec(
                name="low",
                provider="x",
                cost_per_1k_input=0.001,
                cost_per_1k_output=0.001,
                context_window=8000,
                avg_latency_ms=500,
                quality_score=0.3,
                capabilities=[ModelCapability.TEXT],
            )
        )
        router = ModelRouter(registry)
        decision = router.decide(
            RoutingPolicy(min_quality=0.8, user_tier="authenticated"), 100, 100
        )
        self.assertIsNone(decision)

    def test_execute_with_fallback(self):
        registry = ModelRegistry()
        registry.register(
            ModelSpec(
                name="primary",
                provider="x",
                cost_per_1k_input=0.001,
                cost_per_1k_output=0.001,
                context_window=8000,
                avg_latency_ms=500,
                quality_score=0.9,
                capabilities=[ModelCapability.TEXT],
            )
        )
        registry.register(
            ModelSpec(
                name="fallback",
                provider="y",
                cost_per_1k_input=0.001,
                cost_per_1k_output=0.001,
                context_window=8000,
                avg_latency_ms=500,
                quality_score=0.85,
                capabilities=[ModelCapability.TEXT],
            )
        )
        router = ModelRouter(registry)

        async def handler(spec):
            if spec.name == "primary":
                raise RuntimeError("boom")
            return {"ok": True}

        async def run():
            return await router.execute(
                router.decide(
                    RoutingPolicy(min_quality=0.5, user_tier="authenticated"),
                    10,
                    10,
                ),
                handler,
            )

        result = asyncio.run(run())
        self.assertEqual(result["model"], "fallback")
        self.assertEqual(registry.stats("primary")["errors"], 1)
        self.assertEqual(registry.stats("fallback")["calls"], 1)


class SchedulerTest(unittest.TestCase):
    def test_dag_topological(self):
        dag = DAG()
        a = Job(id="a", name="a", handler=_ok)
        b = Job(id="b", name="b", depends_on=["a"], handler=_ok)
        c = Job(id="c", name="c", depends_on=["b"], handler=_ok)
        for j in (a, b, c):
            dag.add(j)
        self.assertEqual(dag.topological(), ["a", "b", "c"])

    def test_run(self):
        scheduler = WorkflowScheduler()
        dag = DAG()
        dag.add(Job(id="a", name="a", handler=_ok))
        dag.add(Job(id="b", name="b", depends_on=["a"], handler=_ok))
        scheduler.load(dag)
        result = asyncio.run(scheduler.run())
        self.assertTrue(result["ok"])
        self.assertEqual(result["succeeded"], 2)

    def test_approval_gate(self):
        scheduler = WorkflowScheduler()
        dag = DAG()
        dag.add(
            Job(
                id="a",
                name="a",
                handler=_ok,
                requires_approval=True,
            )
        )
        scheduler.load(dag)
        result = asyncio.run(scheduler.run())
        self.assertFalse(result["ok"])
        self.assertEqual(result["succeeded"], 0)
        scheduler.approve("a")
        result = asyncio.run(scheduler.run())
        self.assertTrue(result["ok"])

    def test_retry_then_fail(self):
        scheduler = WorkflowScheduler()
        dag = DAG()
        dag.add(Job(id="a", name="a", handler=_fail, max_retries=1))
        scheduler.load(dag)
        result = asyncio.run(scheduler.run())
        self.assertFalse(result["ok"])
        self.assertEqual(result["failed_count"], 1)


async def _ok(job: Job) -> dict:
    return {"ok": True, "job": job.name}


async def _fail(job: Job) -> dict:
    raise RuntimeError("nope")


class AgentTest(unittest.TestCase):
    def test_lifecycle(self):
        bus = get_event_bus()
        bus_history = []
        bus.subscribe("agent.finished", lambda e: bus_history.append(e))
        agent = Agent(AgentSpec(name="planner", role="planner", max_iterations=2))
        result = asyncio.run(agent.run("solve X"))
        self.assertEqual(result["agent"], "planner")
        self.assertEqual(agent.state.value, "idle")
        self.assertGreaterEqual(len(bus_history), 1)

    def test_collaboration(self):
        a = Agent(AgentSpec(name="alice", role="planner"))
        b = Agent(AgentSpec(name="bob", role="executor"))
        asyncio.run(a.send("bob", "task", {"goal": "do X"}, correlation_id="c1"))
        # bob subscribed on construction; messages should land in inbox
        self.assertGreaterEqual(len(b.inbox), 1)


class CostManagerTest(unittest.TestCase):
    def test_record_and_quota(self):
        cm = CostManager()
        cm.set_quota("w1", Quota(requests=2, tokens=1000, cost=10.0))
        cm.record("w1", tokens=500, cost=1.0, requests=1)
        cm.record("w1", tokens=400, cost=0.5, requests=1)
        status = cm.check_quota("w1")
        self.assertEqual(status["requests_used"], 2)
        self.assertEqual(status["tokens_used"], 900)
        self.assertFalse(cm.within_quota("w1", tokens=200))

    def test_estimate_cost(self):
        cm = CostManager()
        cost = cm.estimate_cost(1000, 500, embedding_tokens=200, model="gpt-4o-mini")
        self.assertGreater(cost, 0)


class EvaluationTest(unittest.TestCase):
    def test_record_and_summary(self):
        store = EvaluationStore()
        for i in range(5):
            store.make(
                request_id=f"r{i}",
                workspace_id="w1",
                response_latency_ms=100 + i,
                cost=0.001 * i,
                user_feedback=0.8,
            )
        summary = store.summary("w1")
        self.assertEqual(summary["count"], 5)
        self.assertGreater(summary["response_latency_ms"], 0)


class ObservabilityTest(unittest.TestCase):
    def test_tracer(self):
        tracer = Tracer()
        span = tracer.start("test")
        tracer.end(span)
        self.assertEqual(len(tracer.recent()), 1)
        self.assertEqual(tracer.recent()[0]["name"], "test")

    def test_slo_compliance(self):
        slo = SLOTracker()
        slo.define(SLODefinition("latency", 100, "lt"))
        for v in [50, 60, 200, 70]:
            slo.record("latency", v)
        comp = slo.compliance()
        self.assertEqual(comp["latency"]["samples"], 4)
        self.assertLess(comp["latency"]["compliance"], 1.0)

    def test_metrics(self):
        m = MetricsRegistry()
        m.inc("requests", 3)
        m.observe("latency", 50)
        snap = m.snapshot()
        self.assertEqual(snap["counters"]["requests"], 3)
        self.assertEqual(snap["histograms"]["latency"]["count"], 1)


class KernelHandleTest(unittest.TestCase):
    def test_handle_records_artifact_and_evaluation(self):
        from app.kernel import IntelligenceKernel, KernelRequest, get_intelligence_kernel

        kernel = get_intelligence_kernel()
        # reset to avoid test pollution
        kernel.artifacts = ArtifactRegistry()
        kernel.observability = Observability()
        kernel.cost = CostManager()

        async def handler(decision):
            return {"echo": "ok", "model": decision.name}

        response = asyncio.run(
            kernel.handle(
                KernelRequest(goal="hello", workspace_id="w1"),
                handler,
            )
        )
        self.assertTrue(response.ok)
        self.assertEqual(response.artifacts[0][:3], "art")
        self.assertIsNotNone(response.evaluation_id)
        self.assertGreater(response.cost, 0)


if __name__ == "__main__":
    unittest.main()