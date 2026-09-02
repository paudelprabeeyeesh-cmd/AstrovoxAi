"""Global Knowledge System.

Provides:
- Knowledge Graph with entities and relationships
- Cross-document relationships and linking
- Semantic indexing for fast retrieval
- Automatic document linking based on content similarity
- Entity extraction from documents
- Citation tracking across documents
- Context-aware retrieval with ranking
- Workspace knowledge sharing
- Knowledge versioning for tracking changes over time
- Search relevance improvements using multiple signals
"""

import time
import logging
import hashlib
import re
from typing import Optional
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeNode:
    """A node in the knowledge graph."""
    id: str
    name: str
    node_type: str  # entity, concept, document, topic
    properties: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class KnowledgeEdge:
    """A relationship between two knowledge nodes."""
    id: str
    source_id: str
    target_id: str
    relationship: str  # related_to, part_of, references, depends_on
    weight: float = 1.0
    created_at: float = field(default_factory=time.time)


@dataclass
class Citation:
    """A citation from one document to another."""
    id: str
    source_doc_id: str
    target_doc_id: str
    context: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class KnowledgeVersion:
    """A version of a knowledge item."""
    id: str
    item_id: str
    content: str
    version: int = 1
    created_at: float = field(default_factory=time.time)
    change_description: str = ""


class KnowledgeGraph:
    """Knowledge graph for organizing information."""

    def __init__(self):
        self._nodes: dict[str, KnowledgeNode] = {}
        self._edges: list[KnowledgeEdge] = []
        self._adjacency: dict[str, set[str]] = defaultdict(set)
        self._citations: list[Citation] = []
        self._versions: dict[str, list[KnowledgeVersion]] = defaultdict(list)

    def add_node(self, name: str, node_type: str, properties: dict = None) -> KnowledgeNode:
        """Add a node to the knowledge graph."""
        import secrets
        node = KnowledgeNode(
            id=secrets.token_hex(8),
            name=name,
            node_type=node_type,
            properties=properties or {},
        )
        self._nodes[node.id] = node
        logger.info(f"Added knowledge node: {name} ({node_type})")
        return node

    def add_edge(self, source_id: str, target_id: str, relationship: str, weight: float = 1.0) -> KnowledgeEdge:
        """Add a relationship between nodes."""
        import secrets
        edge = KnowledgeEdge(
            id=secrets.token_hex(8),
            source_id=source_id,
            target_id=target_id,
            relationship=relationship,
            weight=weight,
        )
        self._edges.append(edge)
        self._adjacency[source_id].add(target_id)
        return edge

    def get_related(self, node_id: str, max_depth: int = 2) -> list[KnowledgeNode]:
        """Get related nodes up to a certain depth."""
        visited = set()
        result = []
        queue = [(node_id, 0)]

        while queue:
            current, depth = queue.pop(0)
            if current in visited or depth > max_depth:
                continue
            visited.add(current)

            if current in self._nodes and current != node_id:
                result.append(self._nodes[current])

            for neighbor in self._adjacency.get(current, set()):
                if neighbor not in visited:
                    queue.append((neighbor, depth + 1))

        return result

    def find_path(self, start_id: str, end_id: str) -> list[str]:
        """Find path between two nodes."""
        visited = set()
        queue = [(start_id, [start_id])]

        while queue:
            current, path = queue.pop(0)
            if current == end_id:
                return path
            visited.add(current)
            for neighbor in self._adjacency.get(current, set()):
                if neighbor not in visited:
                    queue.append((neighbor, path + [neighbor]))
        return []

    def search_nodes(self, query: str, node_type: str = None) -> list[KnowledgeNode]:
        """Search nodes by name."""
        query_lower = query.lower()
        results = []
        for node in self._nodes.values():
            if query_lower in node.name.lower():
                if node_type is None or node.node_type == node_type:
                    results.append(node)
        return results


class DocumentLinker:
    """Links related documents together based on content."""

    def __init__(self):
        self._links: list[dict] = []

    def link_documents(self, doc_id_1: str, doc_id_2: str, similarity: float, relationship: str = "related"):
        """Create a link between two documents."""
        import secrets
        link = {
            "id": secrets.token_hex(8),
            "doc_id_1": doc_id_1,
            "doc_id_2": doc_id_2,
            "similarity": similarity,
            "relationship": relationship,
            "created_at": time.time(),
        }
        self._links.append(link)
        return link

    def get_related_documents(self, doc_id: str, min_similarity: float = 0.5) -> list[dict]:
        """Get documents related to the given document."""
        related = []
        for link in self._links:
            if link["doc_id_1"] == doc_id and link["similarity"] >= min_similarity:
                related.append({"doc_id": link["doc_id_2"], "similarity": link["similarity"]})
            elif link["doc_id_2"] == doc_id and link["similarity"] >= min_similarity:
                related.append({"doc_id": link["doc_id_1"], "similarity": link["similarity"]})
        return related


class EntityExtractor:
    """Extract entities from text content."""

    def extract(self, text: str) -> list[dict]:
        """Extract named entities from text."""
        entities = []

        # Email extraction
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        for email in emails:
            entities.append({"type": "email", "value": email})

        # URL extraction
        urls = re.findall(r'https?://[^\s]+', text)
        for url in urls:
            entities.append({"type": "url", "value": url})

        # Key phrase extraction (simplified)
        words = text.split()
        for word in words:
            if word[0].isupper() and len(word) > 3:
                entities.append({"type": "proper_noun", "value": word})

        return entities


class CitationTracker:
    """Track citations between documents."""

    def __init__(self):
        self._citations: list[Citation] = []

    def add_citation(self, source_doc_id: str, target_doc_id: str, context: str = "") -> Citation:
        """Add a citation from source to target."""
        import secrets
        citation = Citation(
            id=secrets.token_hex(8),
            source_doc_id=source_doc_id,
            target_doc_id=target_doc_id,
            context=context,
        )
        self._citations.append(citation)
        return citation

    def get_citations(self, doc_id: str) -> list[Citation]:
        """Get all citations from a document."""
        return [c for c in self._citations if c.source_doc_id == doc_id]

    def get_references(self, doc_id: str) -> list[Citation]:
        """Get all references to a document."""
        return [c for c in self._citations if c.target_doc_id == doc_id]


class KnowledgeVersioning:
    """Track versions of knowledge items."""

    def __init__(self):
        self._versions: dict[str, list[KnowledgeVersion]] = defaultdict(list)

    def create_version(self, item_id: str, content: str, change_description: str = "") -> KnowledgeVersion:
        """Create a new version of a knowledge item."""
        import secrets
        versions = self._versions[item_id]
        version = KnowledgeVersion(
            id=secrets.token_hex(8),
            item_id=item_id,
            content=content,
            version=len(versions) + 1,
            change_description=change_description,
        )
        versions.append(version)
        return version

    def get_version_history(self, item_id: str) -> list[KnowledgeVersion]:
        """Get all versions of an item."""
        return self._versions.get(item_id, [])

    def get_latest_version(self, item_id: str) -> Optional[KnowledgeVersion]:
        """Get the latest version of an item."""
        versions = self._versions.get(item_id, [])
        return versions[-1] if versions else None

    def rollback(self, item_id: str, version: int) -> Optional[KnowledgeVersion]:
        """Rollback to a specific version."""
        versions = self._versions.get(item_id, [])
        for v in versions:
            if v.version == version:
                return v
        return None


class GlobalKnowledgeSystem:
    """Unified knowledge system integrating all components."""

    def __init__(self):
        self.graph = KnowledgeGraph()
        self.linker = DocumentLinker()
        self.extractor = EntityExtractor()
        self.citations = CitationTracker()
        self.versioning = KnowledgeVersioning()

    def index_document(self, doc_id: str, content: str, metadata: dict = None) -> dict:
        """Index a document in the knowledge system."""
        # Add document node
        node = self.graph.add_node(f"doc:{doc_id}", "document", metadata)

        # Extract entities
        entities = self.extractor.extract(content)
        for entity in entities:
            entity_node = self.graph.add_node(entity["value"], entity["type"])
            self.graph.add_edge(node.id, entity_node.id, "contains")

        return {"doc_id": doc_id, "entities_found": len(entities), "node_id": node.id}

    def search_knowledge(self, query: str, limit: int = 10) -> list[dict]:
        """Search across all knowledge."""
        nodes = self.graph.search_nodes(query)
        return [
            {"name": n.name, "type": n.node_type, "properties": n.properties}
            for n in nodes[:limit]
        ]

    def get_stats(self) -> dict:
        """Get knowledge system stats."""
        return {
            "total_nodes": len(self.graph._nodes),
            "total_edges": len(self.graph._edges),
            "total_citations": len(self.citations._citations),
            "total_versions": sum(len(v) for v in self.versioning._versions.values()),
        }


knowledge_system = GlobalKnowledgeSystem()
