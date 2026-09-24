import pytest
from datetime import datetime
import numpy as np
from knowledge_graph.temporal_knowledge import TemporalKnowledgeBase, TemporalFact
from causality.causal_engine import CausalEngine, CausalNode, CausalEdge
from metacognition.metacognitive_monitor import MetacognitiveMonitor
from creativity.creative_generator import CreativeGenerator
from social_intelligence.social_reasoner import SocialReasoner, SocialContext
from ethical_reasoning.ethical_engine import EthicalEngine


class TestIntegratedReasoning:
    def test_temporal_causal_integration(self):
        tk = TemporalKnowledgeBase()
        tk.add_fact(TemporalFact(id="f1", subject="A", predicate="causes", object="B", start_time=datetime(2020, 1, 1), end_time=datetime(2020, 6, 1)))
        engine = CausalEngine()
        engine.add_node(CausalNode(id="A", variable="A"))
        engine.add_node(CausalNode(id="B", variable="B"))
        engine.add_edge(CausalEdge(source="A", target="B", strength=0.8, sign="positive"))
        effect = engine.intervention_effect("B", "A", 10.0)
        assert effect > 0.0
        overlap = tk.temporal_overlap("f1", "f1")
        assert overlap == 1.0

    def test_creative_social_integration(self):
        gen = CreativeGenerator()
        outputs = gen.generate("social event idea", n=2, domain_context=["friends", "party"])
        assert len(outputs) == 2
        reasoner = SocialReasoner()
        ctx = SocialContext(actors=["alice", "bob"], relationship="friend", setting="casual", norms=["fun", "support"])
        insight = reasoner.perspective_take("alice", ctx, ["self:wants fun"])
        assert insight.emotions["valence"] >= 0.0

    def test_ethical_metacognitive_integration(self):
        engine = EthicalEngine()
        result = engine.analyze("privacy-preserving analysis", stakeholders=["users"])
        monitor = MetacognitiveMonitor()
        state = monitor.track("ethics_task", performance=0.85, expected_difficulty=0.5)
        assert result.confidence > 0.0
        assert state.overall > 0.0
