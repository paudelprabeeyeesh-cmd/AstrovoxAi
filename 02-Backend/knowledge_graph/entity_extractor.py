import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class EntityMatch:
    text: str
    entity_type: str
    start: int
    end: int


class EntityExtractor:
    def __init__(self, patterns: Optional[Dict[str, str]] = None):
        self.patterns = patterns or {
            "person": r"\b[A-Z][a-z]+\b",
            "organization": r"\b[A-Z]{2,}\b",
            "date": r"\b\d{4}-\d{2}-\d{2}\b",
            "number": r"\b\d+(?:\.\d+)?\b",
        }

    def extract(self, text: str) -> List[EntityMatch]:
        matches: List[EntityMatch] = []
        for entity_type, pattern in self.patterns.items():
            for match in re.finditer(pattern, text):
                matches.append(
                    EntityMatch(
                        text=match.group(),
                        entity_type=entity_type,
                        start=match.start(),
                        end=match.end(),
                    )
                )
        matches.sort(key=lambda m: (m.start, -m.end))
        return matches

    def extract_types(self, text: str, entity_type: str) -> List[EntityMatch]:
        pattern = self.patterns.get(entity_type)
        if not pattern:
            return []
        return [
            EntityMatch(
                text=m.group(),
                entity_type=entity_type,
                start=m.start(),
                end=m.end(),
            )
            for m in re.finditer(pattern, text)
        ]

    def add_pattern(self, entity_type: str, pattern: str) -> None:
        self.patterns[entity_type] = pattern

    def supported_types(self) -> List[str]:
        return list(self.patterns.keys())
