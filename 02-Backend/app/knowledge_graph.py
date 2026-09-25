import os
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from .knowledge_graph_neo4j import KnowledgeGraphNeo4j


class Entity:
    def __init__(self, id: str, entity_type: str, name: str, properties: Dict[str, Any], created_at: str):
        self.id = id
        self.entity_type = entity_type
        self.name = name
        self.properties = properties
        self.created_at = created_at


class Relationship:
    def __init__(self, id: str, source_id: str, target_id: str, source_name: str, target_name: str, relationship_type: str, created_at: str, properties: Optional[Dict[str, Any]] = None):
        self.id = id
        self.source_id = source_id
        self.target_id = target_id
        self.source_name = source_name
        self.target_name = target_name
        self.relationship_type = relationship_type
        self.properties = properties or {}
        self.created_at = created_at


class KnowledgeGraph:
    def __init__(self):
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        auth = (os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "password"))
        self._kg = KnowledgeGraphNeo4j()
        self._kg.connect(uri, auth)

    def add_entity(self, entity_type: str, name: str, properties: Optional[Dict[str, Any]] = None) -> Entity:
        return self._kg.add_entity(entity_type, name, properties)

    def add_relationship(self, source_id: str, target_id: str, relationship_type: str, properties: Optional[Dict[str, Any]] = None) -> Relationship:
        source_entity = self._entity_by_id(source_id)
        target_entity = self._entity_by_id(target_id)
        if not source_entity or not target_entity:
            raise ValueError("Source or target entity not found")
        return self._kg.add_relationship(source_entity.name, target_entity.name, relationship_type, properties)

    def query_entities(self, entity_type: str, filters: Optional[Dict[str, Any]] = None) -> List[Entity]:
        return self._kg.query_entities(entity_type, filters)

    def get_entity_connections(self, entity_id: str) -> List[Dict[str, Any]]:
        entity = self._entity_by_id(entity_id)
        if not entity:
            return []
        return self._kg.get_entity_connections(entity.name)

    def search(self, query: str, limit: int = 10) -> List[Entity]:
        return self._kg.search(query, limit)

    def _entity_by_id(self, entity_id: str) -> Optional[Entity]:
        with self._kg._driver.session() as session:
            result = session.run(
                "MATCH (e:Entity {id: $id}) RETURN e",
                {"id": entity_id}
            )
            record = result.single()
            if not record:
                return None
            e = record["e"]
            return Entity(
                id=e["id"],
                entity_type=e["entity_type"],
                name=e["name"],
                properties=e["properties"] or {},
                created_at=e["created_at"],
            )
