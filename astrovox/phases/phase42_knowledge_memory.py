"""Factual knowledge base: facts, entities, and relationships."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class KnowledgeTriple:
    """A single knowledge triple (subject, predicate, object)."""
    subject: str
    predicate: str
    object_: str
    confidence: float = 1.0
    source: str = ""
    created: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {"subject": self.subject, "predicate": self.predicate,
                "object": self.object_, "confidence": self.confidence,
                "source": self.source, "created": self.created}


class KnowledgeBase:
    """Factual knowledge memory."""

    def __init__(self):
        self.facts: list[KnowledgeTriple] = []
        self.index: dict[str, list[int]] = {}

    def add(self, subject: str, predicate: str, obj: str,
            confidence: float = 1.0, source: str = "") -> KnowledgeTriple:
        fact = KnowledgeTriple(subject=subject, predicate=predicate,
                               object_=obj, confidence=confidence, source=source)
        self.facts.append(fact)
        for term in [subject, predicate, obj]:
            self.index.setdefault(term.lower(), []).append(len(self.facts) - 1)
        return fact

    def query(self, subject: str | None = None, predicate: str | None = None,
              obj: str | None = None, limit: int = 50) -> list[KnowledgeTriple]:
        results = self.facts
        if subject is not None:
            idx = {i for i in self.index.get(subject.lower(), [])}
            results = [f for i, f in enumerate(results) if i in idx]
        if predicate is not None:
            idx = {i for i in self.index.get(predicate.lower(), [])}
            results = [f for i, f in enumerate(results) if i in idx]
        if obj is not None:
            idx = {i for i in self.index.get(obj.lower(), [])}
            results = [f for i, f in enumerate(results) if i in idx]
        return results[:limit]

    def recall(self, query: str, limit: int = 10) -> list[KnowledgeTriple]:
        """Recall facts matching any term in the query."""
        terms = query.lower().split()
        idx = set()
        for term in terms:
            idx.update(self.index.get(term, []))
        return [self.facts[i] for i in sorted(idx)][:limit]

    def count(self) -> int:
        return len(self.facts)

    def to_dict(self) -> dict:
        return {"facts": [f.to_dict() for f in self.facts]}

    def clear(self) -> None:
        self.facts.clear()
        self.index.clear()
