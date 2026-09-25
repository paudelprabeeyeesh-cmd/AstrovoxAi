import os
import uuid
from typing import Any

from services.knowledge.knowledge_graph_neo4j import KnowledgeGraphNeo4j, Entity, Relationship


class Chunk:
    def __init__(self, id: str, content: str, metadata: dict[str, Any] | None = None, score: float = 0.0):
        self.id = id
        self.content = content
        self.metadata = metadata or {}
        self.score = score


class Graph:
    def __init__(self, entities: list[Entity], relationships: list[Relationship]):
        self.entities = entities
        self.relationships = relationships


class GraphRAG:
    def __init__(self):
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        auth = (os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "password"))
        self._kg = KnowledgeGraphNeo4j()
        self._kg.connect(uri, auth)

    def build_graph(self, documents: list[dict[str, Any]]) -> Graph:
        entities: list[Entity] = []
        relationships: list[Relationship] = []
        entity_map: dict[str, Entity] = {}

        for doc in documents:
            doc_id = doc.get("id", str(uuid.uuid4()))
            content = doc.get("content", "")
            doc_entity = self._kg.add_entity("Document", doc.get("title", f"doc_{doc_id}"), {"doc_id": doc_id})
            entities.append(doc_entity)
            entity_map[doc_id] = doc_entity

            chunks = doc.get("chunks", [content])
            for chunk in chunks:
                chunk_id = str(uuid.uuid4())
                chunk_entity = self._kg.add_entity("Chunk", chunk_id, {"content": chunk[:500], "doc_id": doc_id})
                entities.append(chunk_entity)
                self._kg.add_relationship(doc_entity.name, chunk_entity.name, "CONTAINS")

                for other_id, other_entity in entity_map.items():
                    if other_id != doc_id:
                        rel = self._kg.add_relationship(doc_entity.name, other_entity.name, "RELATED_TO", {"reason": "same_graph"})
                        relationships.append(rel)

        return Graph(entities, relationships)

    def traverse_graph(self, query: str, max_hops: int = 3) -> list[Chunk]:
        results = self._kg.search(query, limit=10)
        chunks: list[Chunk] = []

        for entity in results:
            connections = self._kg.get_entity_connections(entity.name)
            visited = {entity.id}
            current_level = [entity]
            for _ in range(max_hops):
                next_level = []
                for current_entity in current_level:
                    for conn in connections:
                        target_id = conn.get("target_id") or conn.get("source_id")
                        if target_id in visited:
                            continue
                        visited.add(target_id)
                        if conn.get("target_name") and conn["target_name"] != current_entity.name:
                            neighbor_name = conn["target_name"]
                            neighbor = self._entity_by_name(neighbor_name)
                            if neighbor and neighbor.entity_type == "Chunk":
                                chunks.append(Chunk(
                                    id=neighbor.id,
                                    content=neighbor.properties.get("content", ""),
                                    metadata={"source_entity": current_entity.name},
                                    score=1.0 / (_ + 1),
                                ))
                                next_level.append(neighbor)
                current_level = next_level
                connections = []
                for e in current_level:
                    connections.extend(self._kg.get_entity_connections(e.name))

        seen = {c.id for c in chunks}
        return [c for c in chunks if c.id not in seen or seen.remove(c.id)]

    def prune_graph(self, graph: Graph, relevance_threshold: float) -> Graph:
        kept_entities = []
        kept_relationships = []
        for rel in graph.relationships:
            score = rel.properties.get("relevance_score", 0.5)
            if score >= relevance_threshold:
                kept_relationships.append(rel)

        kept_ids = set()
        for rel in kept_relationships:
            kept_ids.add(rel.source_id)
            kept_ids.add(rel.target_id)

        for entity in graph.entities:
            if entity.id in kept_ids or entity.entity_type != "Chunk":
                kept_entities.append(entity)

        return Graph(kept_entities, kept_relationships)

    def _entity_by_name(self, name: str) -> Entity | None:
        with self._kg._driver.session() as session:
            result = session.run("MATCH (e:Entity {name: $name}) RETURN e", {"name": name})
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
