import numpy as np
import pytest
from emergent_abilities.phase_transitions import PhaseTransitionDetector, CapabilityEmergenceTracker


class TestPhaseTransitionDetector:
    def test_abrupt_jump_detection(self):
        detector = PhaseTransitionDetector()
        model_sizes = np.array([1e8, 1e9, 1e10, 1e11, 1e12])
        performances = np.array([0.1, 0.15, 0.9, 0.92, 0.93])
        transition = detector.detect_abrupt_jump(model_sizes, performances)
        assert transition.threshold > 0
        assert transition.abruptness > 0.0

    def test_gradual_increase(self):
        detector = PhaseTransitionDetector()
        model_sizes = np.array([1e8, 1e9, 1e10, 1e11, 1e12])
        performances = np.array([0.1, 0.3, 0.5, 0.7, 0.9])
        transition = detector.detect_abrupt_jump(model_sizes, performances)
        assert transition.abruptness >= 0.0

    def test_single_point(self):
        detector = PhaseTransitionDetector()
        model_sizes = np.array([1e9])
        performances = np.array([0.5])
        transition = detector.detect_abrupt_jump(model_sizes, performances)
        assert transition.threshold == 1e9
        assert transition.abruptness == 0.0

    def test_sorted_input(self):
        detector = PhaseTransitionDetector()
        model_sizes = np.array([1e12, 1e8, 1e10])
        performances = np.array([0.9, 0.1, 0.5])
        transition = detector.detect_abrupt_jump(model_sizes, performances)
        assert transition.threshold > 0

    def test_analyze_all_capabilities(self):
        detector = PhaseTransitionDetector()
        model_sizes = np.array([1e8, 1e9, 1e10, 1e11])
        capability_data = {
            "math": np.array([0.1, 0.2, 0.8, 0.9]),
            "reasoning": np.array([0.05, 0.1, 0.5, 0.7]),
        }
        transitions = detector.analyze_all_capabilities(model_sizes, capability_data)
        assert len(transitions) == 2


class TestCapabilityEmergenceTracker:
    def test_track_emergence(self):
        tracker = CapabilityEmergenceTracker()
        model_sizes = np.array([1e8, 1e9, 1e10, 1e11])
        performances = np.array([0.1, 0.15, 0.85, 0.9])
        transition = tracker.track_emergence("math_reasoning", model_sizes, performances)
        assert transition.capability_name == "math_reasoning"
        assert len(tracker.emergence_history) == 1

    def test_compute_emergence_rate(self):
        tracker = CapabilityEmergenceTracker()
        model_sizes = np.array([1e8, 1e9, 1e10])
        for name, perf in [("a", [0.1, 0.2, 0.9]), ("b", [0.05, 0.3, 0.7])]:
            tracker.track_emergence(name, model_sizes, np.array(perf))
        rate = tracker.compute_emergence_rate()
        assert 0.0 <= rate <= 1.0

    def test_get_capability_order(self):
        tracker = CapabilityEmergenceTracker()
        model_sizes = np.array([1e8, 1e9, 1e10, 1e11])
        tracker.track_emergence("coding", model_sizes, np.array([0.1, 0.2, 0.3, 0.9]))
        tracker.track_emergence("math", model_sizes, np.array([0.05, 0.1, 0.8, 0.85]))
        order = tracker.get_capability_order()
        assert len(order) == 2
        assert order[0] == "math"
        assert order[1] == "coding"
