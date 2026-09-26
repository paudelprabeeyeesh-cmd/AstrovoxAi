"""Hallucination detection using fact-checking and consistency scoring."""

import logging
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class HallucinationResult:
    hallucination_score: float
    flags: list[str]
    evidence: list[str]
    is_hallucination: bool


class FactChecker:
    def __init__(self):
        self._known_facts: dict[str, list[str]] = {
            "capital_of_france": ["paris"],
            "capital_of_usa": ["washington", "washington d.c."],
            "chemical_symbol_gold": ["au"],
            "red_planet": ["mars"],
        }

    def check(self, claim: str, context_keys: Optional[list[str]] = None) -> dict:
        lowered = claim.lower()
        evidence = []
        for key, terms in self._known_facts.items():
            if context_keys and key not in context_keys:
                continue
            if any(term in lowered for term in terms):
                evidence.append(f"matched:{key}")
        confidence = min(len(evidence) * 0.3, 1.0)
        return {"supported": confidence > 0.0, "confidence": confidence, "evidence": evidence}


class ConsistencyScorer:
    def __init__(self):
        self._history: list[str] = []

    def score(self, samples: list[str]) -> float:
        if not samples:
            return 0.0
        token_sets = [set(s.lower().split()) for s in samples]
        if len(token_sets) < 2:
            return 1.0
        intersections = []
        for i in range(len(token_sets)):
            for j in range(i + 1, len(token_sets)):
                inter = token_sets[i] & token_sets[j]
                union = token_sets[i] | token_sets[j]
                intersections.append(len(inter) / len(union) if union else 1.0)
        return sum(intersections) / len(intersections)


class HallucinationDetector:
    def __init__(self):
        self.fact_checker = FactChecker()
        self.consistency_scorer = ConsistencyScorer()

    def detect(self, response: str, context: Optional[dict] = None, sample_responses: Optional[list[str]] = None) -> HallucinationResult:
        flags = []
        evidence = []
        context_keys = list(context.keys()) if context else []

        fact_result = self.fact_checker.check(response, context_keys)
        if not fact_result["supported"] and context_keys:
            flags.append("unsupported_claim")
            evidence.append("No supporting fact found in provided context")

        if sample_responses and len(sample_responses) > 1:
            consistency = self.consistency_scorer.score(sample_responses + [response])
            if consistency < 0.5:
                flags.append("inconsistent_response")
                evidence.append(f"Low consistency score: {consistency:.2f}")

        numeric_claims = re.findall(r"\b\d+(?:\.\d+)?%?\b", response)
        if numeric_claims and context:
            for claim in numeric_claims:
                if claim.lower() not in str(context).lower():
                    flags.append("unsupported_number")
                    evidence.append(f"Unverified numeric claim: {claim}")
                    break

        hallucination_score = min(len(flags) * 0.3 + (0.2 if not fact_result["supported"] else 0.0), 1.0)
        return HallucinationResult(
            hallucination_score=round(hallucination_score, 3),
            flags=flags,
            evidence=evidence,
            is_hallucination=hallucination_score >= 0.5,
        )


hallucination_detector = HallucinationDetector()
