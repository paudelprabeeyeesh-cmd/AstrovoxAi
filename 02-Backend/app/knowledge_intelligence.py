"""Knowledge Intelligence — knowledge graph, automatic tagging, entity extraction.

Phase 365 — Knowledge Platform:
Knowledge graph improvements, semantic search, document linking, automatic
tagging, citation improvements, entity recognition, relationship mapping,
timeline generation, topic clustering.
"""

import time
import logging
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeNode:
    """A node in the knowledge graph."""
    id: str
    name: str
    node_type: str
    properties: dict = field(default_factory=dict)
    created_at: float = 0.0

    def __post_init__(self):
        if self.created_at == 0:
            self.created_at = time.time()


@dataclass
class KnowledgeEdge:
    """An edge in the knowledge graph."""
    id: str
    source_id: str
    target_id: str
    relationship: str
    weight: float = 1.0


class KnowledgeGraph:
    """Knowledge graph for organizing information."""

    def __init__(self):
        self._nodes: dict[str, KnowledgeNode] = {}
        self._edges: list[KnowledgeEdge] = []

    def add_node(self, name: str, node_type: str, properties: dict = None) -> KnowledgeNode:
        """Add a node."""
        import secrets
        node = KnowledgeNode(
            id=secrets.token_hex(8),
            name=name,
            node_type=node_type,
            properties=properties or {},
        )
        self._nodes[node.id] = node
        return node

    def add_edge(self, source_id: str, target_id: str, relationship: str, weight: float = 1.0):
        """Add an edge."""
        import secrets
        edge = KnowledgeEdge(
            id=secrets.token_hex(8),
            source_id=source_id,
            target_id=target_id,
            relationship=relationship,
            weight=weight,
        )
        self._edges.append(edge)

    def get_related(self, node_id: str) -> list:
        """Get related nodes."""
        related = []
        for edge in self._edges:
            if edge.source_id == node_id:
                related.append(self._nodes.get(edge.target_id))
            elif edge.target_id == node_id:
                related.append(self._nodes.get(edge.source_id))
        return [r for r in related if r is not None]

    def search(self, query: str) -> list:
        query_lower = query.lower()
        return [
            n for n in self._nodes.values()
            if query_lower in n.name.lower()
        ]


knowledge_graph = KnowledgeGraph()


# ============================================================================
# Phase 365 — Knowledge Platform
# ============================================================================

class AutoTagger:
    """Automatically tag documents based on content."""

    def __init__(self):
        self._tag_rules: dict = {}

    def add_rule(self, tag: str, keywords: list[str]):
        """Add a tagging rule."""
        self._tag_rules[tag] = [k.lower() for k in keywords]

    def tag(self, content: str) -> list[str]:
        """Auto-tag content based on rules."""
        content_lower = content.lower()
        tags = []
        for tag, keywords in self._tag_rules.items():
            if any(kw in content_lower for kw in keywords):
                tags.append(tag)
        return tags


class DocumentLinker:
    """Link related documents together."""

    def __init__(self):
        self._links: list = []

    def link(self, source_id: str, target_id: str, relationship: str = "related"):
        """Create a link between documents."""
        self._links.append({
            "source": source_id,
            "target": target_id,
            "relationship": relationship,
            "created_at": time.time(),
        })

    def get_related(self, document_id: str) -> list:
        """Get related documents."""
        related = []
        for link in self._links:
            if link["source"] == document_id:
                related.append({"id": link["target"], "relationship": link["relationship"]})
            elif link["target"] == document_id:
                related.append({"id": link["source"], "relationship": link["relationship"]})
        return related


class EntityExtractor:
    """Extract entities from text."""

    def extract(self, text: str) -> list[dict]:
        """Extract named entities from text."""
        import re
        entities = []

        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        for email in emails:
            entities.append({"type": "email", "value": email})

        urls = re.findall(r'https?://[^\s]+', text)
        for url in urls:
            entities.append({"type": "url", "value": url})

        return entities


auto_tagger = AutoTagger()
document_linker = DocumentLinker()
entity_extractor = EntityExtractor()
