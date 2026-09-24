import numpy as np
import pytest
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from cognitive_architecture.cognitive_biases import (
    CognitiveBiasSystem,
    ConfirmationBias,
    AnchoringBias,
    AvailabilityHeuristic,
    DebiasingStrategy,
    BiasInstance,
)


class TestConfirmationBias:
    def test_selects_aligned_evidence(self):
        bias = ConfirmationBias(strength=0.7)
        evidence = [
            {"value": 0.1, "source": "a"},
            {"value": 0.9, "source": "b"},
            {"value": 0.05, "source": "c"},
        ]
        selected = bias.select_evidence(evidence, prior_belief=0.9)
        assert len(selected) > 0
        assert all(e["alignment"] > 0.0 for e in selected)

    def test_empty_evidence(self):
        bias = ConfirmationBias()
        selected = bias.select_evidence([], prior_belief=0.5)
        assert selected == []

    def test_selection_history_logged(self):
        bias = ConfirmationBias()
        bias.select_evidence([{"value": 0.5, "source": "a"}], prior_belief=0.5)
        assert len(bias._selections) == 1


class TestAnchoringBias:
    def test_adjust_estimate_influenced_by_anchor(self):
        bias = AnchoringBias(anchor_influence=0.8)
        result = bias.adjust_estimate(estimate=10.0, anchor=100.0, adjustment=0.0)
        assert result > 50.0

    def test_get_anchor_deviation(self):
        bias = AnchoringBias()
        bias.adjust_estimate(10.0, 100.0, 0.0)
        deviation = bias.get_anchor_deviation(true_value=10.0)
        assert deviation >= 0.0

    def test_no_anchor_log(self):
        bias = AnchoringBias()
        assert bias.get_anchor_deviation(true_value=10.0) == 0.0


class TestAvailabilityHeuristic:
    def test_recency_boosts_score(self):
        avail = AvailabilityHeuristic(recency_weight=0.9)
        events = [{"vividness": 0.5, "relevance": 0.5, "timestamp": time.time()}]
        score = avail.estimate_frequency(events, "query")
        assert score > 0.0

    def test_empty_events(self):
        avail = AvailabilityHeuristic()
        score = avail.estimate_frequency([], "query")
        assert score == 0.0

    def test_older_event_lower_score(self):
        avail = AvailabilityHeuristic(recency_weight=0.9)
        recent = [{"vividness": 0.5, "relevance": 0.5, "timestamp": time.time()}]
        old = [{"vividness": 0.5, "relevance": 0.5, "timestamp": time.time() - 10000}]
        recent_score = avail.estimate_frequency(recent, "q")
        old_score = avail.estimate_frequency(old, "q")
        assert recent_score > old_score


class TestDebiasingStrategy:
    def test_counterfactual_reasoning(self):
        ds = DebiasingStrategy()
        result = ds.counterfactual_reasoning(biased_estimate=0.8, alternative_estimate=0.4, bias_strength=0.6)
        assert 0.0 <= result <= 1.0

    def test_pre_mortem(self):
        ds = DebiasingStrategy()
        result = ds.pre_mortem(plan_quality=0.9, failure_prob=0.3)
        assert result < 0.9

    def test_consider_opposite(self):
        ds = DebiasingStrategy()
        result = ds.consider_opposite(belief=0.9, opposite_evidence=0.3, weight=0.5)
        assert 0.0 <= result <= 1.0

    def test_intervention_stats_empty(self):
        ds = DebiasingStrategy()
        stats = ds.get_intervention_stats()
        assert stats["total"] == 0

    def test_intervention_stats_populated(self):
        ds = DebiasingStrategy()
        ds.counterfactual_reasoning(0.8, 0.4, 0.6)
        stats = ds.get_intervention_stats()
        assert stats["total"] == 1


class TestCognitiveBiasSystem:
    def test_detect_confirmation_bias(self):
        cbs = CognitiveBiasSystem()
        biases = cbs.detect_biases({"filter_evidence": True})
        assert len(biases) >= 1
        assert biases[0].bias_type == "confirmation_bias"

    def test_detect_anchoring(self):
        cbs = CognitiveBiasSystem()
        biases = cbs.detect_biases({"anchor": 100.0})
        assert any(b.bias_type == "anchoring" for b in biases)

    def test_detect_availability(self):
        cbs = CognitiveBiasSystem()
        biases = cbs.detect_biases({"recent_events_only": True})
        assert any(b.bias_type == "availability_heuristic" for b in biases)

    def test_no_biases_detected(self):
        cbs = CognitiveBiasSystem()
        biases = cbs.detect_biases({})
        assert len(biases) == 0

    def test_apply_debiasing_counterfactual(self):
        cbs = CognitiveBiasSystem()
        result = cbs.apply_debiasing(0.8, "counterfactual", alternative=0.4, bias_strength=0.6)
        assert 0.0 <= result <= 1.0

    def test_apply_debiasing_unknown_strategy(self):
        cbs = CognitiveBiasSystem()
        result = cbs.apply_debiasing(0.8, "unknown")
        assert result == 0.8

    def test_bias_report_empty(self):
        cbs = CognitiveBiasSystem()
        report = cbs.get_bias_report()
        assert report["total_biases_detected"] == 0

    def test_bias_report_populated(self):
        cbs = CognitiveBiasSystem()
        cbs.detect_biases({"filter_evidence": True, "anchor": 50.0})
        report = cbs.get_bias_report()
        assert report["total_biases_detected"] >= 1
