from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import math


@dataclass
class ReasoningStep:
    premise: str
    inference_type: str
    conclusion: str
    confidence: float
    supporting_evidence: list[str] = field(default_factory=list)
    counterevidence: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


class AbstractReasoningEngine:
    INFERENCE_TYPES = {
        "deduction",
        "abduction",
        "induction",
        "analogy",
        "counterfactual",
        "causal",
        "probabilistic",
        "modal",
        "temporal",
        "spatial",
        "mathematical",
        "logical_paradox_resolution",
    }

    def __init__(self):
        self.reasoning_chain: list[ReasoningStep] = []
        self.knowledge_graph: dict[str, dict[str, Any]] = {}
        self.axioms: dict[str, float] = {}
        self.inference_history: list[dict[str, Any]] = []
        self.max_chain_depth: int = 12

    def add_axiom(self, axiom: str, certainty: float = 1.0):
        self.axioms[axiom] = max(0.0, min(1.0, certainty))

    def add_knowledge(self, concept: str, relations: list[str], properties: dict[str, Any] | None = None):
        self.knowledge_graph[concept] = {
            "relations": relations,
            "properties": properties or {},
        }

    def deduce(self, premises: list[str], target: str) -> ReasoningStep | None:
        confidence = self._propagate_confidence(premises, "deduction")
        if confidence < 0.3:
            return None
        step = ReasoningStep(
            premise="; ".join(premises),
            inference_type="deduction",
            conclusion=target,
            confidence=confidence,
            supporting_evidence=premises,
        )
        self.reasoning_chain.append(step)
        self.inference_history.append(step.__dict__)
        return step

    def abduce(self, observation: str, hypotheses: list[str]) -> list[ReasoningStep]:
        results = []
        for hypothesis in hypotheses:
            likelihood = self._evaluate_hypothesis_likelihood(observation, hypothesis)
            if likelihood > 0.25:
                step = ReasoningStep(
                    premise=observation,
                    inference_type="abduction",
                    conclusion=hypothesis,
                    confidence=likelihood,
                )
                self.reasoning_chain.append(step)
                results.append(step)
        results.sort(key=lambda r: r.confidence, reverse=True)
        self.inference_history.extend(r.__dict__ for r in results)
        return results

    def induct(self, observations: list[str], generalization: str) -> ReasoningStep | None:
        unique_obs = set(observations)
        coverage = len(unique_obs) / max(len(observations), 1)
        confidence = 0.3 + 0.5 * coverage + 0.2 * min(1.0, len(observations) / 20.0)
        confidence = min(1.0, confidence)
        step = ReasoningStep(
            premise="; ".join(observations[:5]),
            inference_type="induction",
            conclusion=generalization,
            confidence=confidence,
            supporting_evidence=observations,
        )
        self.reasoning_chain.append(step)
        self.inference_history.append(step.__dict__)
        return step

    def counterfactual_reason(self, antecedent: str, consequent: str) -> ReasoningStep:
        plausibility = self._assess_counterfactual_plausibility(antecedent, consequent)
        step = ReasoningStep(
            premise=antecedent,
            inference_type="counterfactual",
            conclusion=consequent,
            confidence=plausibility,
        )
        self.reasoning_chain.append(step)
        self.inference_history.append(step.__dict__)
        return step

    def reason(self, premise: str, target: str, depth: int = 1) -> ReasoningStep | None:
        if depth > self.max_chain_depth:
            return None
        if premise in self.knowledge_graph:
            relations = self.knowledge_graph[premise]["relations"]
            if target in relations:
                step = ReasoningStep(
                    premise=premise,
                    inference_type="deduction",
                    conclusion=target,
                    confidence=0.9,
                )
                self.reasoning_chain.append(step)
                return step
            for related in relations:
                if related in self.knowledge_graph and target in self.knowledge_graph[related]["relations"]:
                    step = ReasoningStep(
                        premise=premise,
                        inference_type="abduction",
                        conclusion=target,
                        confidence=0.7,
                    )
                    self.reasoning_chain.append(step)
                    return step
        return None

    def multi_step_reason(self, steps_definition: list[dict[str, Any]]) -> ReasoningStep | None:
        current_conclusion = None
        for step_def in steps_definition:
            result = self.reason(
                step_def.get("premise", ""),
                step_def.get("target", ""),
                depth=step_def.get("depth", 1),
            )
            if result is None:
                return None
            current_conclusion = result.conclusion
        return current_conclusion

    def _propagate_confidence(self, premises: list[str], inference_type: str) -> float:
        if not premises:
            return 0.0
        base = sum(self.axioms.get(p, 0.5) for p in premises)
        avg = base / len(premises)
        type_mod = {
            "deduction": 1.0,
            "abduction": 0.7,
            "induction": 0.6,
            "analogy": 0.55,
            "counterfactual": 0.5,
            "causal": 0.75,
            "probabilistic": 0.65,
            "modal": 0.6,
        }.get(inference_type, 0.5)
        return min(1.0, avg * type_mod)

    def _evaluate_hypothesis_likelihood(self, observation: str, hypothesis: str) -> float:
        obs_words = set(observation.lower().split())
        hyp_words = set(hypothesis.lower().split())
        overlap = len(obs_words & hyp_words)
        return min(1.0, 0.2 + 0.6 * overlap / max(len(obs_words | hyp_words), 1))

    def _assess_counterfactual_plausibility(self, antecedent: str, consequent: str) -> float:
        ant_words = set(antecedent.lower().split())
        con_words = set(consequent.lower().split())
        similarity = len(ant_words & con_words) / max(len(ant_words | con_words), 1)
        return min(1.0, 0.3 + 0.5 * similarity)

    def get_reasoning_report(self) -> dict[str, Any]:
        type_counts: dict[str, int] = {}
        for step in self.reasoning_chain:
            type_counts[step.inference_type] = type_counts.get(step.inference_type, 0) + 1
        return {
            "total_steps": len(self.reasoning_chain),
            "chain_depth": len(self.reasoning_chain),
            "inference_type_distribution": type_counts,
            "avg_confidence": sum(s.confidence for s in self.reasoning_chain) / max(len(self.reasoning_chain), 1),
            "knowledge_nodes": len(self.knowledge_graph),
            "axioms": len(self.axioms),
        }
