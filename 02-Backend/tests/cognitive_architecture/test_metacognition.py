import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from cognitive_architecture.metacognition import (
    MetacognitiveMonitor,
    LearningAboutLearning,
)


class TestMetacognitiveMonitor:
    def test_evaluate_confidence_within_range(self):
        monitor = MetacognitiveMonitor(confidence_threshold=0.7)
        confidence = monitor.evaluate_confidence(estimate=0.8, uncertainty=0.3)
        assert 0.0 <= confidence <= 1.0

    def test_confidence_decreases_with_uncertainty(self):
        monitor = MetacognitiveMonitor()
        low = monitor.evaluate_confidence(estimate=0.5, uncertainty=0.1)
        high = monitor.evaluate_confidence(estimate=0.5, uncertainty=0.9)
        assert low > high

    def test_record_outcome_updates_history(self):
        monitor = MetacognitiveMonitor()
        monitor.record_outcome(predicted_confidence=0.9, actual_correct=True)
        assert len(monitor.accuracy_history) == 1
        assert monitor.accuracy_history[0] == 1.0

    def test_record_outcome_false(self):
        monitor = MetacognitiveMonitor()
        monitor.record_outcome(predicted_confidence=0.5, actual_correct=False)
        assert monitor.accuracy_history[0] == 0.0

    def test_calibration_error_zero_when_empty(self):
        monitor = MetacognitiveMonitor()
        assert monitor.get_calibration_error() == 0.0

    def test_should_request_help_true(self):
        monitor = MetacognitiveMonitor(confidence_threshold=0.8)
        monitor.evaluate_confidence(estimate=0.1, uncertainty=0.9)
        assert monitor.should_request_help() is True

    def test_should_request_help_false(self):
        monitor = MetacognitiveMonitor(confidence_threshold=0.5)
        monitor.evaluate_confidence(estimate=0.9, uncertainty=0.1)
        assert monitor.should_request_help() is False

    def test_get_metacognitive_state_keys(self):
        monitor = MetacognitiveMonitor()
        monitor.evaluate_confidence(estimate=0.8, uncertainty=0.2)
        state = monitor.get_metacognitive_state()
        assert "current_confidence" in state
        assert "threshold" in state
        assert "accuracy" in state
        assert "needs_help" in state


class TestLearningAboutLearning:
    def test_record_strategy_result(self):
        lol = LearningAboutLearning()
        lol.record_strategy_result("strategy_a", success=True)
        assert "strategy_a" in lol.strategy_performance

    def test_get_best_strategy(self):
        lol = LearningAboutLearning()
        lol.record_strategy_result("strategy_a", success=True)
        lol.record_strategy_result("strategy_a", success=False)
        lol.record_strategy_result("strategy_b", success=True)
        lol.record_strategy_result("strategy_b", success=True)
        best = lol.get_best_strategy()
        assert best == "strategy_b"

    def test_get_best_strategy_empty(self):
        lol = LearningAboutLearning()
        assert lol.get_best_strategy() is None

    def test_estimate_task_difficulty(self):
        lol = LearningAboutLearning()
        difficulty = lol.estimate_task_difficulty("task1", {"complexity": 0.8, "novelty": 0.6})
        assert 0.0 <= difficulty <= 1.0
        assert "task1" in lol.task_difficulty_estimates

    def test_estimate_task_difficulty_empty_features(self):
        lol = LearningAboutLearning()
        difficulty = lol.estimate_task_difficulty("task1", {})
        assert difficulty == 0.5
