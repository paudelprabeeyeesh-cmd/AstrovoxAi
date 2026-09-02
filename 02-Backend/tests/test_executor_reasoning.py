"""Tests for the AI reasoning engine."""

from __future__ import annotations

import unittest

from app.executor.memory_brain import MemoryBrain, MemoryItem, MemoryType
from app.executor.reasoning import (
    ReasoningEngine,
    ReasoningResult,
    ReasoningStep,
    ReasoningStrategy,
    chain_reason,
    debate_reason,
    get_reasoning_engine,
    graph_reason,
    reflection_reason,
    tree_reason,
    verification_reason,
)


class ReasoningStrategiesTest(unittest.TestCase):
    def test_chain(self):
        brain = MemoryBrain()
        brain.remember("auth uses OAuth", type=MemoryType.LONG_TERM, confidence=0.8)
        steps = chain_reason("explain auth", brain.recall("auth"))
        self.assertGreater(len(steps), 0)
        self.assertEqual(steps[0].strategy, ReasoningStrategy.CHAIN)

    def test_tree(self):
        steps = tree_reason("q", [])
        self.assertGreater(len(steps), 0)

    def test_graph(self):
        brain = MemoryBrain()
        a = brain.remember("a", type=MemoryType.LONG_TERM, tags=["x"])
        b = brain.remember("b", type=MemoryType.LONG_TERM, tags=["x"])
        steps = graph_reason("q", [a, b])
        # Two nodes that share a tag should be linked.
        edges = [s for s in steps if s.metadata.get("edges")]
        self.assertGreaterEqual(len(edges), 1)

    def test_debate(self):
        steps = debate_reason("q", [])
        self.assertEqual(len(steps), 3)
        self.assertEqual(steps[2].strategy, ReasoningStrategy.DEBATE)

    def test_reflection(self):
        steps = reflection_reason("q", [])
        self.assertGreater(len(steps), 0)

    def test_verification(self):
        steps = verification_reason("what is x", "x is the answer")
        self.assertEqual(steps[0].strategy, ReasoningStrategy.VERIFICATION)


class ReasoningEngineTest(unittest.TestCase):
    def test_solve(self):
        brain = MemoryBrain()
        brain.remember("the capital of France is Paris", type=MemoryType.LONG_TERM, confidence=0.95)
        engine = ReasoningEngine(brain=brain)
        result = engine.solve("What is the capital of France?")
        self.assertGreater(result.confidence, 0.5)
        self.assertIn(ReasoningStrategy.CHAIN, result.strategies_used)
        self.assertGreater(len(result.facts_used), 0)

    def test_solve_with_custom_strategies(self):
        engine = ReasoningEngine(brain=MemoryBrain())
        result = engine.solve(
            "test",
            strategies=[ReasoningStrategy.DEBATE, ReasoningStrategy.VERIFICATION],
        )
        self.assertEqual(
            set(result.strategies_used),
            {ReasoningStrategy.DEBATE, ReasoningStrategy.VERIFICATION},
        )

    def test_history(self):
        engine = ReasoningEngine(brain=MemoryBrain())
        engine.solve("q1")
        engine.solve("q2")
        self.assertEqual(len(engine.history()), 2)


if __name__ == "__main__":
    unittest.main()