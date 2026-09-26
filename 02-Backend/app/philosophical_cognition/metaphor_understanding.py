from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List


class MetaphorType(str, Enum):
    CONCEPTUAL = "conceptual"
    ONTOLOGICAL = "ontological"
    STRUCTURAL = "structural"
    IMAGERY = "imagery"
    EXPLANATORY = "explanatory"


class MappingRelation(str, Enum):
    IDENTITY = "identity"
    SIMILARITY = "similarity"
    CONTAINMENT = "containment"
    PROCESS = "process"
    CAUSAL = "causal"


@dataclass
class MetaphorMapping:
    source_domain: str
    target_domain: str
    relations: List[MappingRelation]
    entailments: List[str] = field(default_factory=list)
    confidence: float = 0.0
    metaphor_type: MetaphorType = MetaphorType.CONCEPTUAL


@dataclass
class Interpretation:
    literal_meaning: str
    metaphorical_meaning: str
    mappings: List[MetaphorMapping]
    entailments: List[str] = field(default_factory=list)
    coherence_score: float = 0.0


class MetaphorUnderstandingEngine:
    def __init__(self) -> None:
        self.domain_ontologies: Dict[str, Dict[str, float]] = {}

    def register_domain(self, domain: str, concepts: Dict[str, float]) -> None:
        self.domain_ontologies[domain] = concepts

    def extract_mappings(self, source: str, target: str) -> MetaphorMapping:
        mapping = MetaphorMapping(
            source_domain=source,
            target_domain=target,
            relations=[MappingRelation.SIMILARITY],
            confidence=0.8,
        )
        mapping.entailments = [f"{source} structurally mirrors {target}"]
        return mapping

    def interpret(self, utterance: str, context: str) -> Interpretation:
        mapping = self.extract_mappings("language", context)
        return Interpretation(
            literal_meaning=utterance,
            metaphorical_meaning=f"Metaphorical sense of {utterance} in {context}",
            mappings=[mapping],
            entailments=[f"Entailment from mapping: {utterance}"],
            coherence_score=0.75,
        )

    def generate_metaphor(self, target_concept: str, source_domain: str) -> MetaphorMapping:
        return self.extract_mappings(source_domain, target_concept)
