from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from .knowledge_graph import Entity, Relation, KnowledgeGraph


@dataclass
class GraphStore:
    graph: KnowledgeGraph = field(default_factory=KnowledgeGraph)
    snapshot_index: List[str] = field(default_factory=list)

    def add_entity(self, entity: Entity) -> None:
        self.graph.add_entity(entity)

    def add_relation(self, relation: Relation) -> None:
        self.graph.add_relation(relation)

    def remove_entity(self, entity_id: str) -> None:
        if entity_id in self.graph.entities:
            del self.graph.entities[entity_id]
            to_remove = [key for key in self.graph.relations if entity_id in key]
            for key in to_remove:
                del self.graph.relations[key]

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        return self.graph.entities.get(entity_id)

    def list_entities(self) -> List[Entity]:
        return list(self.graph.entities.values())

    def list_relations(self) -> List[Relation]:
        return list(self.graph.relations.values())

    def merge(self, other: "GraphStore") -> None:
        for entity in other.list_entities():
            self.graph.entities[entity.id] = entity
        for relation in other.list_relations():
            key = (relation.source, relation.target, relation.type)
            self.graph.relations[key] = relation

    def snapshot(self, name: str) -> None:
        self.snapshot_index.append(name)

    def entity_count(self) -> int:
        return len(self.graph.entities)

    def relation_count(self) -> int:
        return len(self.graph.relations)
