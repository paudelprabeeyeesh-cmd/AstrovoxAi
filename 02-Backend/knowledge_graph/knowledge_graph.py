from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Set
import numpy as np


@dataclass
class Entity:
    id: str
    name: str
    type: str
    attributes: Dict[str, str] = None

    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {}


@dataclass
class Relation:
    source: str
    target: str
    type: str
    weight: float = 1.0
    attributes: Dict[str, str] = None

    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {}


class KnowledgeGraph:
    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.relations: List[Relation] = {}

    def add_entity(self, entity: Entity) -> None:
        self.entities[entity.id] = entity

    def add_relation(self, relation: Relation) -> None:
        key = (relation.source, relation.target, relation.type)
        self.relations[key] = relation

    def get_neighbors(self, entity_id: str) -> List[Tuple[str, str, float]]:
        neighbors = []
        for (src, tgt, rtype), rel in self.relations.items():
            if src == entity_id:
                neighbors.append((tgt, rtype, rel.weight))
            elif tgt == entity_id:
                neighbors.append((src, rtype, rel.weight))
        return neighbors

    def find_path(self, start: str, end: str, max_depth: int = 5) -> Optional[List[str]]:
        if start not in self.entities or end not in self.entities:
            return None
        queue = [(start, [start])]
        visited = {start}
        while queue:
            current, path = queue.pop(0)
            if current == end:
                return path
            if len(path) >= max_depth:
                continue
            for neighbor, _, _ in self.get_neighbors(current):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        return None

    def shortest_path_length(self, start: str, end: str) -> Optional[int]:
        path = self.find_path(start, end)
        return len(path) - 1 if path else None

    def infer_relations(self) -> List[Relation]:
        inferred = []
        entity_ids = list(self.entities.keys())
        for i, e1 in enumerate(entity_ids):
            for e2 in entity_ids[i + 1 :]:
                if not self._directly_connected(e1, e2):
                    inferred.append(
                        Relation(
                            source=e1,
                            target=e2,
                            type="inferred",
                            weight=0.3,
                            attributes={"method": "transitivity"},
                        )
                    )
        return inferred

    def _directly_connected(self, e1: str, e2: str) -> bool:
        return any(
            (r.source == e1 and r.target == e2) or (r.source == e2 and r.target == e1)
            for r in self.relations.values()
        )

    def get_subgraph(self, center: str, depth: int = 1) -> Tuple[Set[str], List[Relation]]:
        nodes = {center}
        edges = []
        frontier = [center]
        for _ in range(depth):
            next_frontier = []
            for node in frontier:
                for neighbor, rtype, weight in self.get_neighbors(node):
                    if neighbor not in nodes:
                        nodes.add(neighbor)
                        next_frontier.append(neighbor)
                    edges.append(
                        Relation(source=node, target=neighbor, type=rtype, weight=weight)
                    )
            frontier = next_frontier
        return nodes, edges

    def similarity(self, e1: str, e2: str) -> float:
        if e1 not in self.entities or e2 not in self.entities:
            return 0.0
        n1 = set(self.get_neighbors(e1))
        n2 = set(self.get_neighbors(e2))
        if not n1 and not n2:
            return 1.0 if e1 == e2 else 0.0
        if not n1 or not n2:
            return 0.0
        intersection = len(n1 & n2)
        union = len(n1 | n2)
        return intersection / union if union > 0 else 0.0
