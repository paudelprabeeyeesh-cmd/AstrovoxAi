from dataclasses import dataclass, field
from typing import Any


@dataclass
class Metaphor:
    source_domain: str
    target_domain: str
    mapping: dict[str, str]
    aptness: float
    vividness: float


class MetaphorUnderstanding:
    def __init__(self):
        self.metaphors: list[Metaphor] = []
        self.domain_mappings: dict[str, dict[str, str]] = {}

    def interpret(self, metaphor_text: str) -> Metaphor | None:
        parts = metaphor_text.split(" is ")
        if len(parts) != 2:
            return None
        source, target = parts[0].strip(), parts[1].strip()
        mapping = self._generate_mapping(source, target)
        aptness = self._score_aptness(mapping)
        metaphor = Metaphor(
            source_domain=source,
            target_domain=target,
            mapping=mapping,
            aptness=aptness,
            vividness=0.7,
        )
        self.metaphors.append(metaphor)
        return metaphor

    def _generate_mapping(self, source: str, target: str) -> dict[str, str]:
        return {
            f"{source}_structure": f"{target}_structure",
            f"{source}_function": f"{target}_function",
        }

    def _score_aptness(self, mapping: dict[str, str]) -> float:
        return 0.5 + 0.1 * len(mapping)
