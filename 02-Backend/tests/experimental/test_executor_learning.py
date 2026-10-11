"""Tests for the learning engine."""

from __future__ import annotations

import unittest

from app.executor.learning import (
    FeedbackEvent,
    LearningEngine,
    get_learning_engine,
)


class LearningEngineTest(unittest.TestCase):
    def test_record_feedback(self):
        engine = LearningEngine()
        event = engine.record_feedback("response", 0.5, comment="ok")
        self.assertEqual(event.rating, 0.5)
        self.assertEqual(engine.summary()["feedback_count"], 1)

    def test_record_failure(self):
        engine = LearningEngine()
        engine.record_failure("plugin:x", error="boom")
        self.assertEqual(engine.summary()["failures"], 1)

    def test_record_latency(self):
        engine = LearningEngine()
        for ms in [100, 200, 300]:
            engine.record_latency(ms)
        self.assertAlmostEqual(engine.summary()["latency_avg_ms"], 200, places=2)

    def test_record_tool_workflow(self):
        engine = LearningEngine()
        engine.record_tool(True)
        engine.record_tool(False)
        engine.record_workflow(True)
        self.assertEqual(engine.summary()["tool_success_rate"], 0.5)
        self.assertEqual(engine.summary()["workflow_success_rate"], 1.0)

    def test_report_recommendations(self):
        engine = LearningEngine()
        engine.record_feedback("response", -0.5)
        engine.record_retrieval(0.3)
        engine.record_planner(0.4)
        engine.record_tool(False)
        engine.record_workflow(False)
        engine.record_latency(5000)
        engine.record_hallucination("plugin:x", confidence=0.3)
        report = engine.improvement_report()
        self.assertGreater(len(report["recommendations"]), 1)
        self.assertNotIn("No critical issues detected.", report["recommendations"])

    def test_report_no_issues(self):
        engine = LearningEngine()
        engine.record_feedback("response", 0.9)
        engine.record_retrieval(0.9)
        engine.record_planner(0.9)
        engine.record_tool(True)
        engine.record_workflow(True)
        engine.record_latency(100)
        report = engine.improvement_report()
        self.assertEqual(report["recommendations"], ["No critical issues detected."])

    def test_rating_clamp(self):
        engine = LearningEngine()
        event = engine.record_feedback("response", 5.0)
        self.assertEqual(event.rating, 1.0)
        event = engine.record_feedback("response", -5.0)
        self.assertEqual(event.rating, -1.0)


if __name__ == "__main__":
    unittest.main()