from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Metaphor:
    source_domain: str
    target_domain: str
    mapping: dict[str, str]
    aptness: float
    vividness: float
    emotional_resonance: float = 0.0
    cross_domain_richness: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


class MetaphorUnderstanding:
    def __init__(self):
        self.metaphors: list[Metaphor] = []
        self.domain_mappings: dict[str, dict[str, str]] = {}
        self.conceptual_blend_registry: dict[str, list[str]] = {}
        self.interpretation_confidence_threshold: float = 0.4

    def interpret(self, metaphor_text: str) -> Metaphor | None:
        parts = metaphor_text.split(" is ")
        if len(parts) != 2:
            parts = metaphor_text.split(" are ")
        if len(parts) != 2:
            parts = metaphor_text.split(" like ")
        if len(parts) != 2:
            return None
        source, target = parts[0].strip(), parts[1].strip()
        mapping = self._generate_rich_mapping(source, target)
        aptness = self._score_aptness(mapping, source, target)
        vividness = self._score_vividness(mapping)
        emotional_resonance = self._score_emotional_resonance(source, target)
        cross_domain_richness = self._score_cross_domain_richness(source, target)
        metaphor = Metaphor(
            source_domain=source,
            target_domain=target,
            mapping=mapping,
            aptness=aptness,
            vividness=vividness,
            emotional_resonance=emotional_resonance,
            cross_domain_richness=cross_domain_richness,
        )
        self.metaphors.append(metaphor)
        key = f"{source}::{target}"
        self.domain_mappings.setdefault(key, mapping)
        return metaphor

    def generate_metaphor(self, source_domain: str, target_concept: str, style: str = "poetic") -> Metaphor | None:
        mapping = self._generate_rich_mapping(source_domain, target_concept)
        aptness = self._score_aptness(mapping, source_domain, target_concept)
        if aptness < self.interpretation_confidence_threshold:
            return None
        vividness = self._score_vividness(mapping)
        emotional_resonance = self._score_emotional_resonance(source_domain, target_concept)
        cross_domain_richness = self._score_cross_domain_richness(source_domain, target_concept)
        metaphor = Metaphor(
            source_domain=source_domain,
            target_domain=target_concept,
            mapping=mapping,
            aptness=aptness,
            vividness=vividness,
            emotional_resonance=emotional_resonance,
            cross_domain_richness=cross_domain_richness,
        )
        self.metaphors.append(metaphor)
        return metaphor

    def conceptual_blend(self, domain_a: str, domain_b: str) -> dict[str, Any] | None:
        blend_key = f"{domain_a}+{domain_b}"
        if blend_key in self.conceptual_blend_registry:
            return {
                "blend_domain": blend_key,
                "elements": self.conceptual_blend_registry[blend_key],
                "novelty_score": 0.7,
            }
        elements = [
            f"{domain_a}_structure",
            f"{domain_b}_function",
            f"emergent::{domain_a[0]}{domain_b[0]}_property",
        ]
        self.conceptual_blend_registry[blend_key] = elements
        return {
            "blend_domain": blend_key,
            "elements": elements,
            "novelty_score": 0.75,
        }

    def get_metaphor_report(self) -> dict[str, Any]:
        return {
            "total_interpreted": len(self.metaphors),
            "domain_mappings": len(self.domain_mappings),
            "blends": len(self.conceptual_blend_registry),
            "recent": [
                {
                    "source": m.source_domain,
                    "target": m.target_domain,
                    "aptness": m.aptness,
                    "vividness": m.vividness,
                }
                for m in self.metaphors[-5:]
            ],
        }

    def _generate_rich_mapping(self, source: str, target: str) -> dict[str, str]:
        mappings = {
            f"{source}_structure": f"{target}_structure",
            f"{source}_function": f"{target}_function",
            f"{source}_essence": f"{target}_essence",
            f"{source}_dynamics": f"{target}_dynamics",
            f"{source}_boundaries": f"{target}_boundaries",
        }
        if self.domain_mappings:
            last_key = list(self.domain_mappings.keys())[-1]
            prior = self.domain_mappings[last_key]
            for k, v in list(prior.items())[:3]:
                mappings[f"{source}_{k.split('_')[-1]}"] = f"{target}_{v.split('_')[-1]}"
        return mappings

    def _score_aptness(self, mapping: dict[str, str], source: str, target: str) -> float:
        base = 0.3
        coverage_bonus = min(0.4, 0.08 * len(mapping))
        domain_familiarity = 0.15 if source in self.domain_mappings else 0.05
        return min(1.0, base + coverage_bonus + domain_familiarity)

    def _score_vividness(self, mapping: dict[str, str]) -> float:
        sensory_keys = sum(1 for k in mapping if any(w in k.lower() for w in ["color", "sound", "texture", "light", "voice"]))
        return min(1.0, 0.4 + 0.15 * sensory_keys + 0.05 * len(mapping))

    def _score_emotional_resonance(self, source: str, target: str) -> float:
        emotional_keywords = ["love", "pain", "joy", "fear", "hope", "despair", "ecstasy", "grief"]
        combined = f"{source} {target}".lower()
        hits = sum(1 for kw in emotional_keywords if kw in combined)
        return min(1.0, 0.2 + 0.15 * hits)

    def _score_cross_domain_richness(self, source: str, target: str) -> float:
        source_len = len(source.split())
        target_len = len(target.split())
        diversity = abs(source_len - target_len) / max(source_len + target_len, 1)
        return min(1.0, 0.3 + 0.5 * diversity + 0.1 * len(self.metaphors) / max(len(self.metaphors) + 10, 1))
