"""Knowledge graph integration with graph RAG."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Entity:
    entity_id: str
    name: str
    entity_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


@dataclass
class Relationship:
    source_id: str
    target_id: str
    relation: str
    properties: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0


class KnowledgeGraph:
    """Knowledge graph with graph RAG integration."""

    def __init__(self):
        self._entities: Dict[str, Entity] = {}
        self._relationships: List[Relationship] = {}
        self._adjacency: Dict[str, List[str]] = {}

    def add_entity(self, entity: Entity) -> None:
        self._entities[entity.entity_id] = entity

    def add_relationship(self, relationship: Relationship) -> None:
        key = f"{relationship.source_id}->{relationship.target_id}"
        self._relationships[key] = relationship
        self._adjacency.setdefault(relationship.source_id, []).append(relationship.target_id)

    def get_neighbors(self, entity_id: str) -> List[str]:
        return list(self._adjacency.get(entity_id, []))

    def traverse(self, entity_id: str, depth: int = 2) -> List[Entity]:
        visited = set()
        queue = [(entity_id, 0)]
        result = []
        while queue:
            current, d = queue.pop(0)
            if current in visited or d > depth:
                continue
            visited.add(current)
            entity = self._entities.get(current)
            if entity:
                result.append(entity)
            for neighbor in self._adjacency.get(current, []):
                if neighbor not in visited:
                    queue.append((neighbor, d + 1))
        return result

    def query(self, subject: str = None, predicate: str = None, obj: str = None) -> List[Relationship]:
        results = []
        for rel in self._relationships.values():
            if subject and rel.source_id != subject:
                continue
            if predicate and rel.relation != predicate:
                continue
            if obj and rel.target_id != obj:
                continue
            results.append(rel)
        return results

    def subgraph(self, entity_id: str, depth: int = 2) -> Dict[str, Any]:
        entities = self.traverse(entity_id, depth)
        entity_ids = {e.entity_id for e in entities}
        relationships = [r for r in self._relationships.values() if r.source_id in entity_ids or r.target_id in entity_ids]
        return {"entities": entities, "relationships": relationships}

    def get_stats(self) -> Dict[str, Any]:
        return {
            "entities": len(self._entities),
            "relationships": len(self._relationships),
            "avg_degree": sum(len(v) for v in self._adjacency.values()) / max(len(self._adjacency), 1),
        }


_graph: Optional[KnowledgeGraph] = None


def get_knowledge_graph() -> KnowledgeGraph:
    global _graph
    if _graph is None:
        _graph = KnowledgeGraph()
    return _graph
