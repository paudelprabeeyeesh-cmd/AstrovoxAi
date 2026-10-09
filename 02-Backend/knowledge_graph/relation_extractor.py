import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class RelationMatch:
    subject: str
    predicate: str
    object: str
    confidence: float = 1.0


class RelationExtractor:
    def __init__(self, templates: Optional[Dict[str, str]] = None):
        self.templates = templates or {
            "works_for": r"(?P<subject>\w+)\s+works\s+for\s+(?P<object>\w+)",
            "located_in": r"(?P<subject>\w+)\s+is\s+in\s+(?P<object>\w+)",
            "born_in": r"(?P<subject>\w+)\s+was\s+born\s+in\s+(?P<object>\w+)",
        }

    def extract(self, text: str) -> List[RelationMatch]:
        matches: List[RelationMatch] = []
        for predicate, pattern in self.templates.items():
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                matches.append(
                    RelationMatch(
                        subject=match.group("subject"),
                        predicate=predicate,
                        object=match.group("object"),
                        confidence=1.0,
                    )
                )
        return matches

    def extract_by_type(self, text: str, predicate: str) -> List[RelationMatch]:
        pattern = self.templates.get(predicate)
        if not pattern:
            return []
        return [
            RelationMatch(
                subject=m.group("subject"),
                predicate=predicate,
                object=m.group("object"),
                confidence=1.0,
            )
            for m in re.finditer(pattern, text, flags=re.IGNORECASE)
        ]

    def add_template(self, predicate: str, pattern: str) -> None:
        self.templates[predicate] = pattern

    def supported_predicates(self) -> List[str]:
        return list(self.templates.keys())
