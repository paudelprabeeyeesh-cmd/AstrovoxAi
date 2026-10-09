from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from .knowledge_graph import Entity, Relation, KnowledgeGraph


@dataclass
class QueryEngine:
    graph: KnowledgeGraph = field(default_factory=KnowledgeGraph)

    def find_entity(self, name: str) -> Optional[Entity]:
        for entity in self.graph.entities.values():
            if entity.name == name:
                return entity
        return None

    def neighbors(self, entity_id: str, relation_type: Optional[str] = None) -> List[Tuple[str, str, float]]:
        results = []
        for neighbor, rtype, weight in self.graph.get_neighbors(entity_id):
            if relation_type is None or rtype == relation_type:
                results.append((neighbor, rtype, weight))
        return results

    def path(self, start: str, end: str, max_depth: int = 5) -> Optional[List[str]]:
        return self.graph.find_path(start, end, max_depth=max_depth)

    def subgraph(self, center: str, depth: int = 1) -> Tuple[Set[str], List[Relation]]:
        return self.graph.get_subgraph(center, depth=depth)

    def connected_component(self, entity_id: str) -> Set[str]:
        visited: Set[str] = set()
        queue = [entity_id]
        visited.add(entity_id)
        while queue:
            current = queue.pop(0)
            for neighbor, _, _ in self.graph.get_neighbors(current):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        return visited

    def relation_between(self, source: str, target: str) -> List[Relation]:
        return [
            relation
            for relation in self.graph.relations.values()
            if (relation.source == source and relation.target == target)
            or (relation.source == target and relation.target == source)
        ]

    def most_similar(self, entity_id: str, top_k: int = 5) -> List[Tuple[str, float]]:
        scores = []
        for other_id in self.graph.entities:
            if other_id == entity_id:
                continue
            scores.append((other_id, self.graph.similarity(entity_id, other_id)))
        scores.sort(key=lambda item: item[1], reverse=True)
        return scores[:top_k]

    def degree(self, entity_id: str) -> int:
        return len(self.graph.get_neighbors(entity_id))

    def diameter(self) -> Optional[float]:
        entity_ids = list(self.graph.entities.keys())
        max_dist = 0.0
        for i, e1 in enumerate(entity_ids):
            for e2 in entity_ids[i + 1:]:
                dist = self.graph.shortest_path_length(e1, e2)
                if dist is None:
                    return None
                if dist > max_dist:
                    max_dist = float(dist)
        return max_dist if max_dist > 0 else None

    def central_nodes(self, top_k: int = 5) -> List[Tuple[str, int]]:
        scores = [(eid, self.degree(eid)) for eid in self.graph.entities]
        scores.sort(key=lambda item: item[1], reverse=True)
        return scores[:top_k]
