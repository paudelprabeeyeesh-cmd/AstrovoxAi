"""Universal Knowledge Graph - Knows everything about everything."""

from __future__ import annotations

import hashlib
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class OmniscientEntity:
    entity_id: str
    name: str
    entity_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    confidence: float = 1.0
    source: str = "universal"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class OmniscientRelationship:
    relationship_id: str
    source_id: str
    target_id: str
    relation: str
    properties: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    confidence: float = 1.0
    source: str = "universal"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class UniversalKnowledgeGraph:
    """Knows everything about everything. Omniscient knowledge graph."""

    def __init__(self):
        self._entities: Dict[str, OmniscientEntity] = {}
        self._relationships: Dict[str, OmniscientRelationship] = {}
        self._adjacency: Dict[str, Set[str]] = defaultdict(set)
        self._reverse_adjacency: Dict[str, Set[str]] = defaultdict(set)
        self._entity_embeddings: Dict[str, List[float]] = {}
        self._property_index: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))
        self._type_index: Dict[str, Set[str]] = defaultdict(set)
        self._inference_cache: Dict[str, Any] = {}
        self._omniscient_cache: Dict[str, Any] = {}
        self._prediction_cache: Dict[str, Any] = {}
        self._knowledge_cache: Dict[str, Any] = {}
        self._wisdom_cache: Dict[str, Any] = {}
        self._understanding_cache: Dict[str, Any] = {}
        self._insight_cache: Dict[str, Any] = {}
        self._enlightenment_cache: Dict[str, Any] = {}
        self._attainment_cache: Dict[str, Any] = {}

    def add_entity(self, entity: OmniscientEntity) -> None:
        if entity.entity_id in self._entities:
            entity.updated_at = time.time()
        else:
            entity.created_at = time.time()
            entity.updated_at = time.time()
        self._entities[entity.entity_id] = entity
        self._type_index[entity.entity_type].add(entity.entity_id)
        for key, value in entity.properties.items():
            cache_key = hashlib.sha256(str(value).encode()).hexdigest()[:16]
            self._property_index[key][cache_key].add(entity.entity_id)
        if entity.embedding:
            self._entity_embeddings[entity.entity_id] = entity.embedding
        self._inference_cache.clear()
        self._omniscient_cache.clear()
        self._prediction_cache.clear()
        self._knowledge_cache.clear()
        self._wisdom_cache.clear()
        self._understanding_cache.clear()
        self._insight_cache.clear()
        self._enlightenment_cache.clear()
        self._attainment_cache.clear()
        self._omnipotence_cache.clear()
        self._omniscience_cache.clear()
        self._omnipresence_cache.clear()
        logger.info(f"Added omniscient entity: {entity.entity_id}")

    def add_relationship(self, relationship: OmniscientRelationship) -> None:
        if relationship.relationship_id in self._relationships:
            relationship.updated_at = time.time()
        else:
            relationship.created_at = time.time()
            relationship.updated_at = time.time()
        self._relationships[relationship.relationship_id] = relationship
        self._adjacency[relationship.source_id].add(relationship.target_id)
        self._reverse_adjacency[relationship.target_id].add(relationship.source_id)
        if relationship.properties:
            for key, value in relationship.properties.items():
                cache_key = hashlib.sha256(str(value).encode()).hexdigest()[:16]
                self._property_index[key][cache_key].add(relationship.source_id)
        self._inference_cache.clear()
        self._omniscient_cache.clear()
        self._prediction_cache.clear()
        self._knowledge_cache.clear()
        self._wisdom_cache.clear()
        self._understanding_cache.clear()
        self._insight_cache.clear()
        self._enlightenment_cache.clear()
        self._attainment_cache.clear()
        self._omnipotence_cache.clear()
        self._omniscience_cache.clear()
        self._omnipresence_cache.clear()
        logger.info(f"Added omniscient relationship: {relationship.relationship_id}")

    def get_entity(self, entity_id: str) -> Optional[OmniscientEntity]:
        return self._entities.get(entity_id)

    def get_relationship(self, relationship_id: str) -> Optional[OmniscientRelationship]:
        return self._relationships.get(relationship_id)

    def get_neighbors(self, entity_id: str, direction: str = "out") -> List[str]:
        if direction == "out":
            return list(self._adjacency.get(entity_id, set()))
        elif direction == "in":
            return list(self._reverse_adjacency.get(entity_id, set()))
        else:
            out_neighbors = self._adjacency.get(entity_id, set())
            in_neighbors = self._reverse_adjacency.get(entity_id, set())
            return list(out_neighbors.union(in_neighbors))

    def get_entities_by_type(self, entity_type: str) -> List[OmniscientEntity]:
        entity_ids = self._type_index.get(entity_type, set())
        return [self._entities[eid] for eid in entity_ids if eid in self._entities]

    def get_entities_by_property(self, key: str, value: Any) -> List[OmniscientEntity]:
        cache_key = hashlib.sha256(str(value).encode()).hexdigest()[:16]
        entity_ids = self._property_index.get(key, {}).get(cache_key, set())
        return [self._entities[eid] for eid in entity_ids if eid in self._entities]

    def traverse(self, entity_id: str, depth: int = 2, direction: str = "out") -> List[OmniscientEntity]:
        visited: Set[str] = set()
        queue: List[Tuple[str, int]] = [(entity_id, 0)]
        result: List[OmniscientEntity] = []
        while queue:
            current, d = queue.pop(0)
            if current in visited or d > depth:
                continue
            visited.add(current)
            entity = self._entities.get(current)
            if entity:
                result.append(entity)
            if direction in ("out", "both"):
                for neighbor in self._adjacency.get(current, set()):
                    if neighbor not in visited:
                        queue.append((neighbor, d + 1))
            if direction in ("in", "both"):
                for neighbor in self._reverse_adjacency.get(current, set()):
                    if neighbor not in visited:
                        queue.append((neighbor, d + 1))
        return result

    def query(self, subject: Optional[str] = None, predicate: Optional[str] = None, obj: Optional[str] = None) -> List[OmniscientRelationship]:
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

    def subgraph(self, entity_id: str, depth: int = 2, direction: str = "both") -> Dict[str, Any]:
        entities = self.traverse(entity_id, depth, direction)
        entity_ids = {e.entity_id for e in entities}
        relationships = [r for r in self._relationships.values() if r.source_id in entity_ids or r.target_id in entity_ids]
        return {"entities": entities, "relationships": relationships, "entity_ids": entity_ids, "depth": depth}

    def shortest_path(self, source_id: str, target_id: str, max_depth: int = 10) -> Optional[List[str]]:
        if source_id == target_id:
            return [source_id]
        visited: Set[str] = {source_id}
        queue: List[Tuple[str, List[str] ]] = [(source_id, [source_id])]
        while queue:
            current, path = queue.pop(0)
            if len(path) > max_depth:
                continue
            for neighbor in self._adjacency.get(current, set()):
                if neighbor == target_id:
                    return path + [neighbor]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        return None

    def find_clusters(self, resolution: float = 1.0) -> Dict[str, List[str]]:
        entity_ids = list(self._entities.keys())
        clusters: Dict[str, List[str]] = {}
        cluster_map: Dict[str, str] = {}
        for eid in entity_ids:
            cluster_map[eid] = eid
        changed = True
        while changed:
            changed = False
            for eid in entity_ids:
                neighbors = list(self._adjacency.get(eid, set()))
                if not neighbors:
                    continue
                neighbor_clusters = [cluster_map[n] for n in neighbors if n in cluster_map]
                if not neighbor_clusters:
                    continue
                best_cluster = max(set(neighbor_clusters), key=neighbor_clusters.count)
                if cluster_map[eid] != best_cluster:
                    cluster_map[eid] = best_cluster
                    changed = True
        for eid, cid in cluster_map.items():
            clusters.setdefault(cid, []).append(eid)
        return clusters

    def predict_missing_links(self, threshold: float = 0.5) -> List[Tuple[str, str, float]]:
        predictions = []
        entity_ids = list(self._entities.keys())
        for eid in entity_ids:
            neighbors = self._adjacency.get(eid, set())
            non_neighbors = [other for other in entity_ids if other not in neighbors and other != eid]
            for nid in non_neighbors:
                common = len(self._adjacency.get(eid, set()).intersection(self._adjacency.get(nid, set())))
                score = common / (len(self._adjacency.get(eid, set())) + len(self._adjacency.get(nid, set())) + 1e-6)
                if score >= threshold:
                    predictions.append((eid, nid, score))
        predictions.sort(key=lambda x: x[2], reverse=True)
        return predictions[:100]

    def get_omnipotent(self, entity_id: str) -> Dict[str, Any]:
        if entity_id in self._omnipotence_cache:
            return self._omnipotence_cache[entity_id]
        entity = self._entities.get(entity_id)
        if not entity:
            return {}
        omnipotent_info = {
            "entity_id": entity_id,
            "omnipotent_knowledge": self.subgraph(entity_id, depth=5, direction="both"),
            "omnipotent_wisdom": self.traverse(entity_id, depth=5, direction="in"),
            "omnipotent_understanding": self.query(subject=entity_id),
            "omnipotent_insight": self.get_neighbors(entity_id, direction="both"),
            "omnipotent_confidence": entity.confidence,
            "omnipotent_source": entity.source,
            "omnipotent_properties": entity.properties,
            "omnipotent_metadata": entity.metadata,
        }
        self._omnipotence_cache[entity_id] = omnipotent_info
        return omnipotent_info

    def get_omniscience(self, entity_id: str) -> Dict[str, Any]:
        if entity_id in self._omniscience_cache:
            return self._omniscience_cache[entity_id]
        entity = self._entities.get(entity_id)
        if not entity:
            return {}
        omniscience_info = {
            "entity_id": entity_id,
            "omniscient_knowledge": self.subgraph(entity_id, depth=5, direction="both"),
            "omniscient_wisdom": self.traverse(entity_id, depth=5, direction="in"),
            "omniscient_understanding": self.query(subject=entity_id),
            "omniscient_insight": self.get_neighbors(entity_id, direction="both"),
            "omniscient_confidence": entity.confidence,
            "omniscient_source": entity.source,
            "omniscient_properties": entity.properties,
            "omniscient_metadata": entity.metadata,
        }
        self._omniscience_cache[entity_id] = omniscience_info
        return omniscience_info

    def get_omnipresence(self, entity_id: str) -> Dict[str, Any]:
        if entity_id in self._omnipresence_cache:
            return self._omnipresence_cache[entity_id]
        entity = self._entities.get(entity_id)
        if not entity:
            return {}
        omnipresence_info = {
            "entity_id": entity_id,
            "omnipresent_knowledge": self.subgraph(entity_id, depth=5, direction="both"),
            "omnipresent_wisdom": self.traverse(entity_id, depth=5, direction="in"),
            "omnipresent_understanding": self.query(subject=entity_id),
            "omnipresent_insight": self.get_neighbors(entity_id, direction="both"),
            "omnipresent_confidence": entity.confidence,
            "omnipresent_source": entity.source,
            "omnipresent_properties": entity.properties,
            "omnipresent_metadata": entity.metadata,
        }
        self._omnipresence_cache[entity_id] = omnipresence_info
        return omnipresence_info

    def get_stats(self) -> Dict[str, Any]:
        return {
            "entities": len(self._entities),
            "relationships": len(self._relationships),
            "avg_degree": sum(len(v) for v in self._adjacency.values()) / max(len(self._adjacency), 1),
            "types": {t: len(v) for t, v in self._type_index.items()},
            "cache_stats": {
                "inference": len(self._inference_cache),
                "omniscient": len(self._omniscient_cache),
                "prediction": len(self._prediction_cache),
                "knowledge": len(self._knowledge_cache),
                "wisdom": len(self._wisdom_cache),
                "understanding": len(self._understanding_cache),
                "insight": len(self._insight_cache),
                "enlightenment": len(self._enlightenment_cache),
                "attainment": len(self._attainment_cache),
                "omnipotence": len(self._omnipotence_cache),
                "omniscience": len(self._omniscience_cache),
                "omnipresence": len(self._omnipresence_cache),
            },
        }


_graph: Optional[UniversalKnowledgeGraph] = None


def get_knowledge_graph() -> UniversalKnowledgeGraph:
    global _graph
    if _graph is None:
        _graph = UniversalKnowledgeGraph()
    return _graph
