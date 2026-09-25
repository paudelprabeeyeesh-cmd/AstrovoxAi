import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

try:
    from neo4j import GraphDatabase
except ImportError:
    GraphDatabase = None


class Entity:
    def __init__(self, id: str, entity_type: str, name: str, properties: Dict[str, Any], created_at: str):
        self.id = id
        self.entity_type = entity_type
        self.name = name
        self.properties = properties
        self.created_at = created_at


class Relationship:
    def __init__(self, id: str, source_id: str, target_id: str, source_name: str, target_name: str, relationship_type: str, properties: Dict[str, Any], created_at: str):
        self.id = id
        self.source_id = source_id
        self.target_id = target_id
        self.source_name = source_name
        self.target_name = target_name
        self.relationship_type = relationship_type
        self.properties = properties
        self.created_at = created_at


class KnowledgeGraphNeo4j:
    def __init__(self):
        self._driver = None
        self._connected = False

    def connect(self, uri: str, auth: tuple) -> bool:
        if GraphDatabase is None:
            return False
        try:
            self._driver = GraphDatabase.driver(uri, auth=auth)
            with self._driver.session() as session:
                session.run("RETURN 1")
            self._connected = True
            return True
        except Exception:
            self._connected = False
            return False

    def close(self):
        if self._driver:
            self._driver.close()

    def add_entity(self, entity_type: str, name: str, properties: Optional[Dict[str, Any]] = None) -> Entity:
        entity_id = str(uuid.uuid4())
        props = properties or {}
        with self._driver.session() as session:
            session.run(
                """
                CREATE (e:Entity {
                    id: $id,
                    entity_type: $entity_type,
                    name: $name,
                    properties: $properties,
                    created_at: $created_at
                })
                """,
                {
                    "id": entity_id,
                    "entity_type": entity_type,
                    "name": name,
                    "properties": props,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        return Entity(entity_id, entity_type, name, props, datetime.now(timezone.utc).isoformat())

    def add_relationship(self, source_name: str, target_name: str, relationship_type: str, properties: Optional[Dict[str, Any]] = None) -> Relationship:
        rel_id = str(uuid.uuid4())
        props = properties or {}
        with self._driver.session() as session:
            result = session.run(
                """
                MATCH (a:Entity {name: $source_name}), (b:Entity {name: $target_name})
                CREATE (a)-[r:RELATIONSHIP {
                    id: $id,
                    relationship_type: $relationship_type,
                    properties: $properties,
                    created_at: $created_at
                }]->(b)
                RETURN r.id AS id, a.id AS source_id, b.id AS target_id
                """,
                {
                    "id": rel_id,
                    "source_name": source_name,
                    "target_name": target_name,
                    "relationship_type": relationship_type,
                    "properties": props,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            record = result.single()
        return Relationship(
            record["id"],
            record["source_id"],
            record["target_id"],
            source_name,
            target_name,
            relationship_type,
            props,
            datetime.now(timezone.utc).isoformat(),
        )

    def query_entities(self, entity_type: str, filters: Optional[Dict[str, Any]] = None) -> List[Entity]:
        cypher = "MATCH (e:Entity {entity_type: $entity_type}) RETURN e"
        params: Dict[str, Any] = {"entity_type": entity_type}
        if filters and "name" in filters:
            cypher = "MATCH (e:Entity) WHERE e.entity_type = $entity_type AND e.name CONTAINS $name RETURN e"
            params["name"] = filters["name"]
        with self._driver.session() as session:
            result = session.run(cypher, params)
            return [
                Entity(
                    id=record["e"]["id"],
                    entity_type=record["e"]["entity_type"],
                    name=record["e"]["name"],
                    properties=record["e"]["properties"] or {},
                    created_at=record["e"]["created_at"],
                )
                for record in result
            ]

    def get_entity_connections(self, entity_name: str) -> List[Dict[str, Any]]:
        with self._driver.session() as session:
            result = session.run(
                """
                MATCH (a:Entity {name: $name})-[r:RELATIONSHIP]-(b:Entity)
                RETURN r, a, b
                """,
                {"name": entity_name}
            )
            connections = []
            for record in result:
                rel = record["r"]
                a = record["a"]
                b = record["b"]
                connections.append({
                    "id": rel["id"],
                    "source_id": a["id"],
                    "source_name": a["name"],
                    "target_id": b["id"],
                    "target_name": b["name"],
                    "relationship_type": rel["relationship_type"],
                    "created_at": rel["created_at"],
                })
            return connections

    def search(self, query: str, limit: int = 10) -> List[Entity]:
        with self._driver.session() as session:
            result = session.run(
                """
                MATCH (e:Entity)
                WHERE e.name CONTAINS $query OR any(propKey IN keys(e.properties) WHERE e.properties[propKey] CONTAINS $query)
                RETURN e
                LIMIT $limit
                """,
                {"query": query, "limit": limit}
            )
            return [
                Entity(
                    id=record["e"]["id"],
                    entity_type=record["e"]["entity_type"],
                    name=record["e"]["name"],
                    properties=record["e"]["properties"] or {},
                    created_at=record["e"]["created_at"],
                )
                for record in result
            ]
