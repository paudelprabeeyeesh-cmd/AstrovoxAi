"""Knowledge graph construction and querying for RAG pipelines."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeTriple:
    subject: str
    predicate: str
    obj: str
    properties: Dict[str, Any] = field(default_factory=dict)


class KnowledgeGraph:
    """Knowledge graph for entity-relation extraction and graph-based retrieval."""

    def __init__(self):
        self.triples: List[KnowledgeTriple] = []
        self.entities: Dict[str, Dict[str, Any]] = {}
        self.relations: Dict[str, List[str]] = {}

    def add_triple(self, subject: str, predicate: str, obj: str, properties: Optional[Dict[str, Any]] = None) -> None:
        triple = KnowledgeTriple(subject=subject, predicate=predicate, obj=obj, properties=properties or {})
        self.triples.append(triple)
        self.entities.setdefault(subject, {"type": "entity", "name": subject})
        self.entities.setdefault(obj, {"type": "entity", "name": obj})
        self.relations.setdefault(predicate, []).append(subject)

    def extract_from_text(self, text: str) -> List[KnowledgeTriple]:
        triples = []
        sentences = re.split(r"(?<=[.!?])\s+", text)
        for sentence in sentences:
            entities = self._extract_entities(sentence)
            relations = self._extract_relations(sentence)
            for subj in entities:
                for pred in relations:
                    for obj in entities:
                        if subj != obj:
                            triples.append(KnowledgeTriple(subject=subj, predicate=pred, obj=obj))
        for t in triples:
            self.add_triple(t.subject, t.predicate, t.obj, t.properties)
        return triples

    def query(self, subject: Optional[str] = None, predicate: Optional[str] = None, obj: Optional[str] = None) -> List[KnowledgeTriple]:
        results = []
        for triple in self.triples:
            if subject and triple.subject != subject:
                continue
            if predicate and triple.predicate != predicate:
                continue
            if obj and triple.obj != obj:
                continue
            results.append(triple)
        return results

    def get_neighbors(self, entity_id: str, direction: str = "both") -> List[str]:
        neighbors = set()
        for triple in self.triples:
            if direction in ("out", "both") and triple.subject == entity_id:
                neighbors.add(triple.obj)
            if direction in ("in", "both") and triple.obj == entity_id:
                neighbors.add(triple.subject)
        return list(neighbors)

    def path_between(self, source: str, target: str, max_hops: int = 3) -> Optional[List[str]]:
        visited = {source}
        queue = [(source, [source])]
        while queue:
            current, path = queue.pop(0)
            if len(path) > max_hops:
                continue
            if current == target:
                return path
            for neighbor in self.get_neighbors(current):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": self.entities,
            "triples": [{"subject": t.subject, "predicate": t.predicate, "object": t.obj} for t in self.triples],
        }

    @staticmethod
    def _extract_entities(text: str) -> List[str]:
        matches = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text)
        return list(dict.fromkeys(matches))

    @staticmethod
    def _extract_relations(text: str) -> List[str]:
        patterns = [
            r"\b(is|are|was|were|has|have|had|contains|contains|relates to|depends on|belongs to|located in|created by)\b",
        ]
        relations = []
        for pattern in patterns:
            relations.extend(re.findall(pattern, text, flags=re.IGNORECASE))
        return list(dict.fromkeys(r.lower() for r in relations))
