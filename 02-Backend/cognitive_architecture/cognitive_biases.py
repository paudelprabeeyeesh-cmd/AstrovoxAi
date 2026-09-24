import time
import numpy as np
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field


@dataclass
class BiasInstance:
    bias_type: str
    strength: float
    context: Dict[str, Any]
    impact: float
    detected_at: float = field(default_factory=time.time)


class ConfirmationBias:
    def __init__(self, strength: float = 0.7):
        self.strength = strength
        self._selections: List[Dict[str, Any]] = []

    def select_evidence(self, evidence: List[Dict[str, Any]], prior_belief: float) -> List[Dict[str, Any]]:
        scored = []
        for e in evidence:
            alignment = 1.0 - abs(e.get("value", 0.5) - prior_belief)
            bias_score = alignment * self.strength
            scored.append({**e, "bias_score": bias_score, "alignment": alignment})
        scored.sort(key=lambda x: x["bias_score"], reverse=True)
        selected = [e for e in scored if e["bias_score"] > 0.3]
        self._selections.append({
            "prior_belief": prior_belief,
            "selected_count": len(selected),
            "total_count": len(evidence),
        })
        return selected


class AnchoringBias:
    def __init__(self, anchor_influence: float = 0.6):
        self.anchor_influence = anchor_influence
        self._anchor_log: List[Dict[str, Any]] = []

    def adjust_estimate(self, estimate: float, anchor: float, adjustment: float) -> float:
        biased = anchor * self.anchor_influence + estimate * (1.0 - self.anchor_influence) + adjustment
        self._anchor_log.append({
            "anchor": anchor,
            "raw_estimate": estimate,
            "biased_estimate": biased,
            "timestamp": time.time(),
        })
        return biased

    def get_anchor_deviation(self, true_value: float) -> float:
        if not self._anchor_log:
            return 0.0
        deviations = [abs(entry["biased_estimate"] - true_value) for entry in self._anchor_log]
        return float(np.mean(deviations))


class AvailabilityHeuristic:
    def __init__(self, recency_weight: float = 0.8, vividness_weight: float = 0.5):
        self.recency_weight = recency_weight
        self.vividness_weight = vividness_weight
        self._retrieval_log: List[Dict[str, Any]] = []

    def estimate_frequency(self, events: List[Dict[str, Any]], query: str) -> float:
        if len(events) == 0:
            return 0.0
        scores = []
        current_time = time.time()
        for event in events:
            recency = 1.0 / (1.0 + (current_time - event.get("timestamp", current_time)))
            vividness = event.get("vividness", 0.5)
            relevance = event.get("relevance", 0.5)
            score = (self.recency_weight * recency + self.vividness_weight * vividness + 0.5 * relevance)
            scores.append(score)
        estimated_freq = np.mean(scores)
        self._retrieval_log.append({
            "query": query,
            "estimated_freq": estimated_freq,
            "events_considered": len(events),
        })
        return estimated_freq


class DebiasingStrategy:
    def __init__(self):
        self._interventions: List[Dict[str, Any]] = []

    def counterfactual_reasoning(self, biased_estimate: float, alternative_estimate: float,
                                  bias_strength: float) -> float:
        adjusted = biased_estimate - bias_strength * (biased_estimate - alternative_estimate)
        self._interventions.append({
            "type": "counterfactual",
            "before": biased_estimate,
            "after": adjusted,
            "timestamp": time.time(),
        })
        return adjusted

    def pre_mortem(self, plan_quality: float, failure_prob: float) -> float:
        adjusted = plan_quality * (1.0 - failure_prob * 0.5)
        self._interventions.append({
            "type": "pre_mortem",
            "before": plan_quality,
            "after": adjusted,
            "timestamp": time.time(),
        })
        return adjusted

    def consider_opposite(self, belief: float, opposite_evidence: float, weight: float = 0.5) -> float:
        adjusted = belief * (1.0 - weight) + opposite_evidence * weight
        self._interventions.append({
            "type": "consider_opposite",
            "before": belief,
            "after": adjusted,
            "timestamp": time.time(),
        })
        return adjusted

    def get_intervention_stats(self) -> Dict[str, Any]:
        if not self._interventions:
            return {"total": 0}
        types = [i["type"] for i in self._interventions]
        return {
            "total": len(self._interventions),
            "by_type": {t: types.count(t) for t in set(types)},
        }


class CognitiveBiasSystem:
    def __init__(self):
        self.confirmation_bias = ConfirmationBias()
        self.anchoring_bias = AnchoringBias()
        self.availability = AvailabilityHeuristic()
        self.debiasing = DebiasingStrategy()
        self._bias_log: List[BiasInstance] = []

    def detect_biases(self, decision_context: Dict[str, Any]) -> List[BiasInstance]:
        biases = []
        if decision_context.get("filter_evidence", False):
            biases.append(BiasInstance(
                bias_type="confirmation_bias",
                strength=self.confirmation_bias.strength,
                context=decision_context,
                impact=0.6,
            ))
        if "anchor" in decision_context:
            biases.append(BiasInstance(
                bias_type="anchoring",
                strength=self.anchoring_bias.anchor_influence,
                context=decision_context,
                impact=0.5,
            ))
        if decision_context.get("recent_events_only", False):
            biases.append(BiasInstance(
                bias_type="availability_heuristic",
                strength=self.availability.recency_weight,
                context=decision_context,
                impact=0.4,
            ))
        self._bias_log.extend(biases)
        return biases

    def apply_debiasing(self, biased_value: float, strategy: str, **kwargs) -> float:
        if strategy == "counterfactual":
            return self.debiasing.counterfactual_reasoning(
                biased_value, kwargs.get("alternative", 0.5), kwargs.get("bias_strength", 0.5)
            )
        if strategy == "pre_mortem":
            return self.debiasing.pre_mortem(biased_value, kwargs.get("failure_prob", 0.3))
        if strategy == "consider_opposite":
            return self.debiasing.consider_opposite(
                biased_value, kwargs.get("opposite_evidence", 1.0 - biased_value)
            )
        return biased_value

    def get_bias_report(self) -> Dict[str, Any]:
        if not self._bias_log:
            return {"total_biases_detected": 0}
        bias_counts = {}
        for b in self._bias_log:
            bias_counts[b.bias_type] = bias_counts.get(b.bias_type, 0) + 1
        return {
            "total_biases_detected": len(self._bias_log),
            "by_type": bias_counts,
            "interventions": self.debiasing.get_intervention_stats(),
        }
