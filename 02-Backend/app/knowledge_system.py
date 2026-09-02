"""Global Knowledge System.

Provides:
- Knowledge Graph with entities and relationships
- Cross-document relationships and linking
- Semantic indexing for fast retrieval
- Automatic document linking based on content similarity
- Entity extraction from documents (regex + pattern-based)
- Citation tracking across documents
- Context-aware retrieval with ranking
- Workspace knowledge sharing
- Knowledge versioning for tracking changes over time
- Search relevance improvements using multiple signals
- Knowledge analytics and visualization
- Batch/incremental indexing pipeline
"""

import time
import logging
import hashlib
import re
import difflib
from typing import Optional
from dataclasses import dataclass, field
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)


RELATIONSHIP_TYPES = {
    "related_to", "part_of", "references", "depends_on", "contains",
    "cites", "cited_by", "derived_from", "supersedes", "contradicts",
    "similar_to", "authored_by", "tagged_with", "belongs_to",
    "temporal_neighbor",
}

NODE_TYPES = {"entity", "concept", "document", "topic", "person", "organization", "date", "number", "term"}


@dataclass
class KnowledgeNode:
    """A node in the knowledge graph."""
    id: str
    name: str
    node_type: str
    properties: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    workspace_id: str = "default"
    is_public: bool = False
    aliases: list[str] = field(default_factory=list)
    occurrence_count: int = 1


@dataclass
class KnowledgeEdge:
    """A relationship between two knowledge nodes."""
    id: str
    source_id: str
    target_id: str
    relationship: str
    weight: float = 1.0
    properties: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    workspace_id: str = "default"


@dataclass
class Citation:
    """A citation from one document to another."""
    id: str
    source_doc_id: str
    target_doc_id: str
    context: str = ""
    locator: str = ""
    created_at: float = field(default_factory=time.time)
    workspace_id: str = "default"


@dataclass
class KnowledgeVersion:
    """A version of a knowledge item."""
    id: str
    item_id: str
    content: str
    version: int = 1
    created_at: float = field(default_factory=time.time)
    change_description: str = ""
    author: str = ""
    diff: str = ""


@dataclass
class DocumentRelationship:
    """An inferred relationship between two documents."""
    id: str
    doc_id_1: str
    doc_id_2: str
    relationship: str
    strength: float
    shared_entities: list[str] = field(default_factory=list)
    temporal_proximity: float = 0.0
    citation_overlap: int = 0
    created_at: float = field(default_factory=time.time)


@dataclass
class IndexJob:
    """Tracks a document indexing job."""
    id: str
    doc_ids: list[str]
    status: str = "pending"
    started_at: float = field(default_factory=time.time)
    completed_at: float = 0.0
    indexed: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


class KnowledgeGraph:
    """Knowledge graph for organizing information."""

    def __init__(self):
        self._nodes: dict[str, KnowledgeNode] = {}
        self._edges: list[KnowledgeEdge] = []
        self._adjacency: dict[str, set[str]] = defaultdict(set)
        self._reverse_adjacency: dict[str, set[str]] = defaultdict(set)
        self._name_index: dict[str, str] = {}
        self._citations: list[Citation] = []
        self._versions: dict[str, list[KnowledgeVersion]] = defaultdict(list)
        self._workspace_index: dict[str, set[str]] = defaultdict(set)

    def add_node(self, name: str, node_type: str, properties: dict = None,
                 workspace_id: str = "default", is_public: bool = False,
                 aliases: list[str] = None, node_id: str = None) -> KnowledgeNode:
        """Add a node to the knowledge graph; merges with existing by name+type."""
        import secrets
        name_key = f"{workspace_id}:{node_type}:{name.lower()}"
        if name_key in self._name_index:
            existing = self._nodes[self._name_index[name_key]]
            existing.occurrence_count += 1
            existing.updated_at = time.time()
            if aliases:
                for alias in aliases:
                    if alias not in existing.aliases:
                        existing.aliases.append(alias)
            if properties:
                existing.properties.update(properties)
            return existing

        node = KnowledgeNode(
            id=node_id or secrets.token_hex(8),
            name=name,
            node_type=node_type,
            properties=properties or {},
            workspace_id=workspace_id,
            is_public=is_public,
            aliases=aliases or [],
        )
        self._nodes[node.id] = node
        self._name_index[name_key] = node.id
        self._workspace_index[workspace_id].add(node.id)
        logger.debug(f"Added knowledge node: {name} ({node_type}) in workspace {workspace_id}")
        return node

    def merge_nodes(self, primary_id: str, secondary_id: str) -> Optional[KnowledgeNode]:
        """Merge two nodes, keeping primary and absorbing secondary."""
        primary = self._nodes.get(primary_id)
        secondary = self._nodes.get(secondary_id)
        if not primary or not secondary or primary_id == secondary_id:
            return primary
        primary.occurrence_count += secondary.occurrence_count
        primary.aliases = list(set(primary.aliases + [secondary.name] + secondary.aliases))
        primary.properties.update(secondary.properties)
        primary.updated_at = time.time()
        for edge in list(self._edges):
            if edge.source_id == secondary_id:
                edge.source_id = primary_id
            elif edge.target_id == secondary_id:
                edge.target_id = primary_id
        self._adjacency.pop(secondary_id, None)
        self._reverse_adjacency.pop(secondary_id, None)
        name_key = f"{secondary.workspace_id}:{secondary.node_type}:{secondary.name.lower()}"
        self._name_index.pop(name_key, None)
        self._workspace_index[secondary.workspace_id].discard(secondary_id)
        del self._nodes[secondary_id]
        return primary

    def add_edge(self, source_id: str, target_id: str, relationship: str, weight: float = 1.0,
                 properties: dict = None, workspace_id: str = "default") -> KnowledgeEdge:
        """Add a relationship between nodes."""
        import secrets
        for existing in self._edges:
            if (existing.source_id == source_id and existing.target_id == target_id
                    and existing.relationship == relationship):
                existing.weight = min(10.0, existing.weight + weight)
                existing.updated_at = time.time() if hasattr(existing, "updated_at") else existing.created_at
                return existing
        edge = KnowledgeEdge(
            id=secrets.token_hex(8),
            source_id=source_id,
            target_id=target_id,
            relationship=relationship,
            weight=weight,
            properties=properties or {},
            workspace_id=workspace_id,
        )
        self._edges.append(edge)
        self._adjacency[source_id].add(target_id)
        self._reverse_adjacency[target_id].add(source_id)
        return edge

    def get_related(self, node_id: str, max_depth: int = 2,
                    relationship: Optional[str] = None) -> list[dict]:
        """Get related nodes up to a certain depth, optionally filtered by relationship type."""
        visited: set[str] = set()
        result: list[dict] = []
        queue: list[tuple[str, int]] = [(node_id, 0)]

        while queue:
            current, depth = queue.pop(0)
            if current in visited or depth > max_depth:
                continue
            visited.add(current)

            if current != node_id and current in self._nodes:
                edge_rel = None
                for e in self._edges:
                    if e.source_id == current and e.target_id == node_id:
                        edge_rel = e.relationship
                        break
                if relationship is None or edge_rel == relationship:
                    result.append({
                        "node": self._nodes[current],
                        "depth": depth,
                        "relationship": edge_rel,
                    })

            for neighbor in self._adjacency.get(current, set()):
                if neighbor not in visited:
                    queue.append((neighbor, depth + 1))
        return result

    def find_path(self, start_id: str, end_id: str) -> list[str]:
        """Find shortest path between two nodes."""
        if start_id == end_id:
            return [start_id]
        visited: set[str] = set()
        queue: list[tuple[str, list[str]]] = [(start_id, [start_id])]

        while queue:
            current, path = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            if current == end_id:
                return path
            for neighbor in self._adjacency.get(current, set()):
                if neighbor not in visited:
                    queue.append((neighbor, path + [neighbor]))
        return []

    def search_nodes(self, query: str, node_type: str = None,
                     workspace_id: Optional[str] = None) -> list[KnowledgeNode]:
        """Search nodes by name substring match."""
        query_lower = query.lower()
        results = []
        for node in self._nodes.values():
            if workspace_id and node.workspace_id != workspace_id and not node.is_public:
                continue
            name_match = query_lower in node.name.lower()
            alias_match = any(query_lower in a.lower() for a in node.aliases)
            if name_match or alias_match:
                if node_type is None or node.node_type == node_type:
                    results.append(node)
        return results

    def get_statistics(self) -> dict:
        """Compute graph statistics: node/edge counts, density, degree, types."""
        node_count = len(self._nodes)
        edge_count = len(self._edges)
        type_counter: Counter = Counter(n.node_type for n in self._nodes.values())
        rel_counter: Counter = Counter(e.relationship for e in self._edges)
        degrees = [len(self._adjacency.get(nid, set())) + len(self._reverse_adjacency.get(nid, set()))
                   for nid in self._nodes]
        avg_degree = (sum(degrees) / node_count) if node_count else 0.0
        max_degree = max(degrees) if degrees else 0
        density = (2.0 * edge_count) / (node_count * (node_count - 1)) if node_count > 1 else 0.0
        top_entities = [
            {"name": n.name, "count": n.occurrence_count}
            for n in sorted(self._nodes.values(), key=lambda x: x.occurrence_count, reverse=True)[:10]
        ]
        return {
            "node_count": node_count,
            "edge_count": edge_count,
            "density": round(density, 4),
            "avg_degree": round(avg_degree, 2),
            "max_degree": max_degree,
            "node_types": dict(type_counter),
            "relationship_types": dict(rel_counter),
            "workspaces": {wid: len(ids) for wid, ids in self._workspace_index.items()},
            "top_entities": top_entities,
        }

    def export_json(self) -> dict:
        """Export graph in JSON-friendly structure."""
        return {
            "nodes": [
                {
                    "id": n.id, "name": n.name, "type": n.node_type,
                    "workspace_id": n.workspace_id, "properties": n.properties,
                    "occurrences": n.occurrence_count,
                }
                for n in self._nodes.values()
            ],
            "edges": [
                {
                    "id": e.id, "source": e.source_id, "target": e.target_id,
                    "relationship": e.relationship, "weight": e.weight,
                }
                for e in self._edges
            ],
        }

    def export_graphviz(self) -> str:
        """Generate Graphviz DOT representation."""
        lines = ["digraph KnowledgeGraph {"]
        for n in self._nodes.values():
            safe = n.name.replace('"', "'")
            lines.append(f'  "{n.id}" [label="{safe}", type="{n.node_type}"];')
        for e in self._edges:
            lines.append(f'  "{e.source_id}" -> "{e.target_id}" '
                         f'[label="{e.relationship}", weight="{e.weight:.2f}"];')
        lines.append("}")
        return "\n".join(lines)

    def extract_subgraph(self, center_id: str, radius: int = 1) -> dict:
        """Extract subgraph around a center node."""
        if center_id not in self._nodes:
            return {"nodes": [], "edges": []}
        related = self.get_related(center_id, max_depth=radius)
        keep_ids = {center_id} | {r["node"].id for r in related}
        nodes = [n for n in self._nodes.values() if n.id in keep_ids]
        edges = [e for e in self._edges if e.source_id in keep_ids and e.target_id in keep_ids]
        return {
            "nodes": [
                {"id": n.id, "name": n.name, "type": n.node_type}
                for n in nodes
            ],
            "edges": [
                {"source": e.source_id, "target": e.target_id,
                 "relationship": e.relationship, "weight": e.weight}
                for e in edges
            ],
        }

    def detect_clusters(self, max_clusters: int = 10) -> list[dict]:
        """Simple label-propagation-style clustering by node_type."""
        clusters: dict[str, list[str]] = defaultdict(list)
        for node in self._nodes.values():
            key = f"{node.node_type}:{node.workspace_id}"
            clusters[key].append(node.id)
        result = []
        for key, members in list(clusters.items())[:max_clusters]:
            internal_edges = [
                e for e in self._edges
                if e.source_id in members and e.target_id in members
            ]
            density = (2.0 * len(internal_edges)) / (len(members) * (len(members) - 1)) if len(members) > 1 else 0
            result.append({
                "label": key,
                "size": len(members),
                "internal_edges": len(internal_edges),
                "density": round(density, 4),
                "members": members[:20],
            })
        result.sort(key=lambda c: c["size"], reverse=True)
        return result


class DocumentLinker:
    """Links related documents together based on content and metadata."""

    def __init__(self):
        self._links: list[DocumentRelationship] = []

    def link_documents(self, doc_id_1: str, doc_id_2: str, similarity: float,
                       relationship: str = "related", shared_entities: list[str] = None,
                       temporal_proximity: float = 0.0, citation_overlap: int = 0,
                       workspace_id: str = "default") -> DocumentRelationship:
        """Create a link between two documents."""
        import secrets
        for existing in self._links:
            if {existing.doc_id_1, existing.doc_id_2} == {doc_id_1, doc_id_2}:
                existing.strength = min(10.0, existing.strength + similarity)
                if shared_entities:
                    existing.shared_entities = list(set(existing.shared_entities + shared_entities))
                existing.citation_overlap += citation_overlap
                return existing
        link = DocumentRelationship(
            id=secrets.token_hex(8),
            doc_id_1=doc_id_1,
            doc_id_2=doc_id_2,
            relationship=relationship,
            strength=similarity,
            shared_entities=shared_entities or [],
            temporal_proximity=temporal_proximity,
            citation_overlap=citation_overlap,
        )
        link.workspace_id = workspace_id
        self._links.append(link)
        return link

    def get_related_documents(self, doc_id: str, min_similarity: float = 0.5) -> list[dict]:
        """Get documents related to the given document."""
        related = []
        for link in self._links:
            if link.strength < min_similarity:
                continue
            if link.doc_id_1 == doc_id:
                related.append({
                    "doc_id": link.doc_id_2, "similarity": link.strength,
                    "relationship": link.relationship, "shared_entities": link.shared_entities,
                })
            elif link.doc_id_2 == doc_id:
                related.append({
                    "doc_id": link.doc_id_1, "similarity": link.strength,
                    "relationship": link.relationship, "shared_entities": link.shared_entities,
                })
        related.sort(key=lambda r: r["similarity"], reverse=True)
        return related

    def infer_relationships(self, doc_metadata: dict[str, dict],
                          shared_entity_index: dict[str, set[str]]) -> list[DocumentRelationship]:
        """Infer pairwise document relationships from shared entities and metadata."""
        new_links = []
        doc_ids = list(doc_metadata.keys())
        for i, d1 in enumerate(doc_ids):
            for d2 in doc_ids[i + 1:]:
                shared = shared_entity_index.get(d1, set()) & shared_entity_index.get(d2, set())
                if not shared:
                    continue
                strength = min(1.0, len(shared) / 10.0)
                t1 = doc_metadata[d1].get("timestamp", 0)
                t2 = doc_metadata[d2].get("timestamp", 0)
                proximity = 0.0
                if t1 and t2:
                    proximity = max(0.0, 1.0 - abs(t1 - t2) / (30 * 86400))
                rel = self.link_documents(
                    d1, d2,
                    similarity=strength,
                    relationship="shared_entities",
                    shared_entities=list(shared)[:10],
                    temporal_proximity=proximity,
                )
                new_links.append(rel)
        return new_links


class EntityExtractor:
    """Pattern-based entity extraction with normalization and deduplication."""

    PATTERNS = {
        "email": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'),
        "url": re.compile(r'https?://[^\s<>"\']+'),
        "ipv4": re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
        "hashtag": re.compile(r'#\w+'),
        "mention": re.compile(r'@\w+'),
        "date_iso": re.compile(r'\b\d{4}-\d{2}-\d{2}\b'),
        "date_us": re.compile(r'\b\d{1,2}/\d{1,2}/\d{2,4}\b'),
        "time": re.compile(r'\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?\b'),
        "currency": re.compile(r'[$€£¥]\s*\d+(?:[.,]\d{2})?(?:\s?(?:USD|EUR|GBP|JPY))?'),
        "percentage": re.compile(r'\b\d+(?:\.\d+)?%'),
        "phone": re.compile(r'\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}'),
        "version": re.compile(r'\bv?\d+\.\d+(?:\.\d+)?\b'),
        "hex_color": re.compile(r'#[0-9A-Fa-f]{6}\b'),
        "uuid": re.compile(r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b'),
        "proper_noun": re.compile(r'\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]+)*\b'),
        "acronym": re.compile(r'\b[A-Z]{2,6}\b'),
    }

    STOPWORDS = {"the", "and", "for", "with", "this", "that", "from", "have", "has", "was", "were", "are"}

    def extract(self, text: str) -> list[dict]:
        """Extract entities using multi-pattern recognition with dedup."""
        entities: dict[tuple[str, str], dict] = {}

        for etype, pattern in self.PATTERNS.items():
            for match in pattern.finditer(text):
                value = match.group(0).strip()
                if not value or value.lower() in self.STOPWORDS:
                    continue
                key = (etype, value.lower())
                if key not in entities:
                    entities[key] = {
                        "type": etype,
                        "value": value,
                        "normalized": self._normalize(etype, value),
                        "positions": [match.start()],
                    }
                else:
                    entities[key]["positions"].append(match.start())

        result = list(entities.values())
        for ent in result:
            ent["frequency"] = len(ent.pop("positions"))
        return result

    def extract_with_metadata(self, text: str, doc_id: str = "",
                              workspace_id: str = "default") -> list[dict]:
        """Extract entities and attach doc/workspace context."""
        entities = self.extract(text)
        for ent in entities:
            ent["doc_id"] = doc_id
            ent["workspace_id"] = workspace_id
        return entities

    def _normalize(self, etype: str, value: str) -> str:
        """Normalize entity value for deduplication."""
        if etype == "url":
            return value.rstrip("/").lower()
        if etype == "email":
            return value.lower()
        if etype in ("date_iso", "date_us", "time"):
            return value
        if etype in ("currency", "percentage", "number", "version"):
            return value.replace(" ", "").replace(",", "")
        return value.strip().lower()

    def deduplicate(self, entities: list[dict]) -> list[dict]:
        """Collapse entities that normalize to the same value within same type."""
        seen: dict[tuple[str, str], dict] = {}
        for ent in entities:
            key = (ent["type"], ent.get("normalized", ent["value"].lower()))
            if key in seen:
                seen[key]["frequency"] = seen[key].get("frequency", 1) + ent.get("frequency", 1)
                if ent["value"] not in seen[key].get("aliases", []):
                    seen[key].setdefault("aliases", [seen[key]["value"]]).append(ent["value"])
            else:
                seen[key] = dict(ent)
        return list(seen.values())


class CitationTracker:
    """Track citations, references, and citation graph between documents."""

    def __init__(self):
        self._citations: list[Citation] = []
        self._citation_index: dict[str, list[Citation]] = defaultdict(list)
        self._reference_index: dict[str, list[Citation]] = defaultdict(list)

    def add_citation(self, source_doc_id: str, target_doc_id: str, context: str = "",
                     locator: str = "", workspace_id: str = "default") -> Citation:
        """Add a citation from source to target."""
        import secrets
        citation = Citation(
            id=secrets.token_hex(8),
            source_doc_id=source_doc_id,
            target_doc_id=target_doc_id,
            context=context,
            locator=locator,
            workspace_id=workspace_id,
        )
        self._citations.append(citation)
        self._citation_index[source_doc_id].append(citation)
        self._reference_index[target_doc_id].append(citation)
        return citation

    def get_citations(self, doc_id: str) -> list[Citation]:
        """Get all citations from a document (papers/references this doc makes)."""
        return list(self._citation_index.get(doc_id, []))

    def get_references(self, doc_id: str) -> list[Citation]:
        """Get all references to a document (papers that cite this doc)."""
        return list(self._reference_index.get(doc_id, []))

    def build_citation_graph(self) -> dict:
        """Build a citation graph: nodes = docs, edges = citation relationships."""
        nodes = set()
        edges = []
        for c in self._citations:
            nodes.add(c.source_doc_id)
            nodes.add(c.target_doc_id)
            edges.append({
                "source": c.source_doc_id, "target": c.target_doc_id,
                "weight": 1.0, "citation_id": c.id,
            })
        return {"nodes": [{"id": n} for n in nodes], "edges": edges}

    def resolve_reference(self, doc_id: str, locator: str) -> Optional[Citation]:
        """Resolve a reference locator (e.g. 'section:3.2', 'page:12') to a citation."""
        for c in self._citation_index.get(doc_id, []):
            if c.locator == locator:
                return c
        return None

    def format_citation(self, citation: Citation, style: str = "APA") -> str:
        """Format a citation in APA or MLA style."""
        ctx = citation.context or "no context"
        if style.upper() == "APA":
            return f"({citation.source_doc_id}, cited in {citation.target_doc_id}) — {ctx}"
        if style.upper() == "MLA":
            return f"{citation.source_doc_id}. \"{ctx}.\" {citation.target_doc_id}."
        return f"[{citation.source_doc_id} -> {citation.target_doc_id}] {ctx}"


class KnowledgeVersioning:
    """Track versions of knowledge items with diff, rollback, and audit trail."""

    def __init__(self):
        self._versions: dict[str, list[KnowledgeVersion]] = defaultdict(list)
        self._audit: list[dict] = []

    def _audit_log(self, action: str, item_id: str, version: int, author: str = ""):
        self._audit.append({
            "action": action,
            "item_id": item_id,
            "version": version,
            "author": author,
            "timestamp": time.time(),
        })

    def create_version(self, item_id: str, content: str, change_description: str = "",
                       author: str = "") -> KnowledgeVersion:
        """Create a new version with diff against previous."""
        import secrets
        versions = self._versions[item_id]
        previous_content = versions[-1].content if versions else ""
        diff = "\n".join(difflib.unified_diff(
            previous_content.splitlines(),
            content.splitlines(),
            lineterm="",
            n=2,
            fromfile=f"v{len(versions)}",
            tofile=f"v{len(versions) + 1}",
        ))
        version = KnowledgeVersion(
            id=secrets.token_hex(8),
            item_id=item_id,
            content=content,
            version=len(versions) + 1,
            change_description=change_description,
            author=author,
            diff=diff,
        )
        versions.append(version)
        self._audit_log("create", item_id, version.version, author)
        return version

    def get_version_history(self, item_id: str) -> list[KnowledgeVersion]:
        """Get all versions of an item, newest last."""
        return list(self._versions.get(item_id, []))

    def get_latest_version(self, item_id: str) -> Optional[KnowledgeVersion]:
        """Get the latest version of an item."""
        versions = self._versions.get(item_id, [])
        return versions[-1] if versions else None

    def get_version(self, item_id: str, version: int) -> Optional[KnowledgeVersion]:
        """Get a specific version of an item."""
        for v in self._versions.get(item_id, []):
            if v.version == version:
                return v
        return None

    def rollback(self, item_id: str, version: int, author: str = "system") -> Optional[KnowledgeVersion]:
        """Rollback by appending the old version's content as a new version."""
        target = self.get_version(item_id, version)
        if not target:
            return None
        new_version = self.create_version(
            item_id=item_id,
            content=target.content,
            change_description=f"Rollback to v{version}",
            author=author,
        )
        self._audit_log("rollback", item_id, new_version.version, author)
        return new_version

    def compare(self, item_id: str, v1: int, v2: int) -> dict:
        """Compare two versions and return their diff."""
        a = self.get_version(item_id, v1)
        b = self.get_version(item_id, v2)
        if not a or not b:
            return {"error": "version_not_found"}
        diff = "\n".join(difflib.unified_diff(
            a.content.splitlines(),
            b.content.splitlines(),
            lineterm="",
            fromfile=f"v{v1}",
            tofile=f"v{v2}",
        ))
        return {
            "from_version": v1,
            "to_version": v2,
            "diff": diff,
            "from_author": a.author,
            "to_author": b.author,
            "from_timestamp": a.created_at,
            "to_timestamp": b.created_at,
        }

    def get_audit_trail(self, item_id: str = "") -> list[dict]:
        """Get audit trail, optionally filtered by item."""
        if not item_id:
            return list(self._audit)
        return [a for a in self._audit if a["item_id"] == item_id]


class IndexingPipeline:
    """Batch and incremental indexing for documents."""

    def __init__(self, knowledge_system: "GlobalKnowledgeSystem"):
        self.knowledge_system = knowledge_system
        self._jobs: dict[str, IndexJob] = {}
        self._indexed_docs: set[str] = set()
        self._last_reindex: float = 0.0

    def index_batch(self, documents: list[dict], workspace_id: str = "default") -> IndexJob:
        """Index a batch of documents."""
        import secrets
        job = IndexJob(id=secrets.token_hex(8), doc_ids=[d.get("doc_id", "") for d in documents])
        job.status = "running"
        self._jobs[job.id] = job

        for doc in documents:
            doc_id = doc.get("doc_id", "")
            content = doc.get("content", "")
            metadata = doc.get("metadata") or {}
            metadata["workspace_id"] = workspace_id
            try:
                self.knowledge_system.index_document(doc_id, content, metadata, workspace_id)
                job.indexed += 1
                self._indexed_docs.add(doc_id)
            except Exception as e:  # noqa: BLE001
                job.failed += 1
                job.errors.append(f"{doc_id}: {e}")

        job.status = "completed" if job.failed == 0 else "partial"
        job.completed_at = time.time()
        return job

    def incremental_update(self, doc_id: str, content: str,
                           workspace_id: str = "default") -> dict:
        """Update an existing document incrementally."""
        metadata = {"workspace_id": workspace_id, "incremental": True}
        result = self.knowledge_system.index_document(doc_id, content, metadata, workspace_id)
        result["incremental"] = True
        return result

    def get_job_status(self, job_id: str) -> Optional[IndexJob]:
        return self._jobs.get(job_id)

    def optimize_index(self) -> dict:
        """Optimize the index by removing orphan nodes and recomputing statistics."""
        referenced = set()
        for edge in self.knowledge_system.graph._edges:
            referenced.add(edge.source_id)
            referenced.add(edge.target_id)
        orphans = [n.id for n in self.knowledge_system.graph._nodes.values()
                   if n.node_type != "document" and n.id not in referenced]
        for nid in orphans:
            del self.knowledge_system.graph._nodes[nid]
        self._last_reindex = time.time()
        return {"removed_orphans": len(orphans), "reindexed_at": self._last_reindex}

    def should_reindex(self, interval_seconds: float = 3600.0) -> bool:
        return (time.time() - self._last_reindex) > interval_seconds


class GlobalKnowledgeSystem:
    """Unified knowledge system integrating all components."""

    def __init__(self):
        self.graph = KnowledgeGraph()
        self.linker = DocumentLinker()
        self.extractor = EntityExtractor()
        self.citations = CitationTracker()
        self.versioning = KnowledgeVersioning()
        self.indexer = IndexingPipeline(self)
        self._query_history: list[dict] = []
        self._shared_public_nodes: set[str] = set()
        self._doc_entity_index: dict[str, set[str]] = defaultdict(set)
        self._doc_metadata: dict[str, dict] = {}

    def index_document(self, doc_id: str, content: str, metadata: dict = None,
                       workspace_id: str = "default") -> dict:
        """Index a document in the knowledge system."""
        metadata = dict(metadata or {})
        metadata.setdefault("workspace_id", workspace_id)
        metadata.setdefault("timestamp", time.time())
        metadata.setdefault("doc_id", doc_id)
        is_public = bool(metadata.pop("is_public", False))

        node = self.graph.add_node(
            f"doc:{doc_id}", "document", metadata,
            workspace_id=workspace_id, is_public=is_public,
            node_id=f"doc:{doc_id}",
        )
        self._doc_metadata[doc_id] = metadata

        entities = self.extractor.extract_with_metadata(content, doc_id=doc_id, workspace_id=workspace_id)
        for entity in entities:
            entity_node = self.graph.add_node(
                entity["value"], entity["type"],
                properties={"normalized": entity["normalized"]},
                workspace_id=workspace_id,
                is_public=is_public,
            )
            self.graph.add_edge(node.id, entity_node.id, "contains", weight=entity.get("frequency", 1))
            self._doc_entity_index[doc_id].add(entity_node.id)

        return {
            "doc_id": doc_id, "entities_found": len(entities),
            "node_id": node.id, "workspace_id": workspace_id,
            "is_public": is_public,
        }

    def search_knowledge(self, query: str, limit: int = 10,
                          workspace_id: Optional[str] = None,
                          boost_recent: bool = True) -> list[dict]:
        """Search across all knowledge with workspace scoping."""
        start = time.time()
        nodes = self.graph.search_nodes(query, workspace_id=workspace_id)
        now = time.time()

        results = []
        for n in nodes:
            score = 1.0
            if boost_recent:
                age_days = (now - n.updated_at) / 86400
                score += max(0.0, 0.5 - age_days * 0.01)
            score += n.occurrence_count * 0.1
            results.append({
                "name": n.name, "type": n.node_type,
                "score": round(score, 4),
                "occurrences": n.occurrence_count,
                "workspace_id": n.workspace_id,
            })
        results.sort(key=lambda r: r["score"], reverse=True)

        self._query_history.append({
            "query": query, "ts": start, "duration_ms": (time.time() - start) * 1000,
            "results": len(results), "workspace_id": workspace_id,
        })
        return results[:limit]

    def context_aware_search(self, query: str, context: dict = None,
                              limit: int = 10) -> list[dict]:
        """Search with query expansion, recency weighting, and personalization signals."""
        start = time.time()
        context = context or {}
        workspace_id = context.get("workspace_id")
        user_id = context.get("user_id", "")
        boost_terms = context.get("boost_terms", [])

        expanded_query = self._expand_query(query)
        nodes = self.graph.search_nodes(expanded_query, workspace_id=workspace_id)
        now = time.time()

        results = []
        for n in nodes:
            score = 1.0
            age_days = (now - n.updated_at) / 86400
            score += max(0.0, 1.0 - age_days * 0.02)
            score += n.occurrence_count * 0.1
            for term in boost_terms:
                if term.lower() in n.name.lower():
                    score += 0.5
            if user_id and user_id in n.properties.get("viewed_by", []):
                score += 0.3
            results.append({
                "name": n.name, "type": n.node_type,
                "score": round(score, 4),
                "occurrences": n.occurrence_count,
                "workspace_id": n.workspace_id,
            })

        diversified = self._diversify_results(results)
        self._query_history.append({
            "query": query, "ts": start, "duration_ms": (time.time() - start) * 1000,
            "results": len(diversified), "context_aware": True,
        })
        return diversified[:limit]

    def _expand_query(self, query: str) -> str:
        """Expand query with related synonyms (simple heuristic)."""
        synonyms = {
            "ml": "machine learning ai", "ai": "artificial intelligence ml",
            "db": "database sql", "api": "endpoint service",
            "doc": "document article", "auth": "authentication authorization login",
        }
        tokens = query.lower().split()
        expanded = list(tokens)
        for t in tokens:
            if t in synonyms:
                expanded.extend(synonyms[t].split())
        return " ".join(expanded)

    def _diversify_results(self, results: list[dict], max_per_type: int = 3) -> list[dict]:
        """Diversify so no single node_type dominates."""
        seen_by_type: Counter = Counter()
        diversified = []
        for r in results:
            if seen_by_type[r["type"]] < max_per_type:
                diversified.append(r)
                seen_by_type[r["type"]] += 1
        for r in results:
            if r not in diversified:
                diversified.append(r)
        return diversified

    def infer_document_relationships(self) -> list[DocumentRelationship]:
        """Infer document-document relationships using shared entities & metadata."""
        return self.linker.infer_relationships(self._doc_metadata, self._doc_entity_index)

    def get_stats(self) -> dict:
        """Get knowledge system stats."""
        return {
            "total_nodes": len(self.graph._nodes),
            "total_edges": len(self.graph._edges),
            "total_citations": len(self.citations._citations),
            "total_versions": sum(len(v) for v in self.versioning._versions.values()),
            "total_documents": len(self._doc_metadata),
            "total_index_jobs": len(self.indexer._jobs),
            "queries_executed": len(self._query_history),
        }

    def get_analytics(self) -> dict:
        """Knowledge analytics dashboard data."""
        graph_stats = self.graph.get_statistics()
        type_counts = Counter(n.node_type for n in self.graph._nodes.values())
        rel_counts = Counter(e.relationship for e in self.graph._edges)
        workspace_counts = Counter(n.workspace_id for n in self.graph._nodes.values())

        query_durations = [q["duration_ms"] for q in self._query_history]
        avg_query_ms = (sum(query_durations) / len(query_durations)) if query_durations else 0.0

        recent_growth = self._compute_growth()
        coverage = self._compute_coverage()

        return {
            "graph": graph_stats,
            "node_type_distribution": dict(type_counts),
            "relationship_distribution": dict(rel_counts),
            "workspace_distribution": dict(workspace_counts),
            "query_performance": {
                "total_queries": len(self._query_history),
                "avg_duration_ms": round(avg_query_ms, 2),
                "p95_duration_ms": round(sorted(query_durations)[int(len(query_durations) * 0.95)] if query_durations else 0.0, 2),
            },
            "growth": recent_growth,
            "coverage": coverage,
            "documents_indexed": len(self._doc_metadata),
            "indexing_jobs": len(self.indexer._jobs),
            "shared_public_nodes": len(self._shared_public_nodes),
        }

    def _compute_growth(self, window_seconds: float = 86400.0) -> dict:
        """Compute growth of nodes/edges/documents within a time window."""
        now = time.time()
        new_nodes = sum(1 for n in self.graph._nodes.values() if now - n.created_at < window_seconds)
        new_edges = sum(1 for e in self.graph._edges if now - e.created_at < window_seconds)
        new_docs = sum(1 for m in self._doc_metadata.values()
                       if now - m.get("timestamp", 0) < window_seconds)
        return {
            "window_seconds": window_seconds,
            "new_nodes": new_nodes,
            "new_edges": new_edges,
            "new_documents": new_docs,
        }

    def _compute_coverage(self) -> dict:
        """Compute entity coverage statistics."""
        total_docs = len(self._doc_metadata)
        if total_docs == 0:
            return {"total_documents": 0, "avg_entities_per_doc": 0.0, "coverage_ratio": 0.0}
        entity_counts = [len(ents) for ents in self._doc_entity_index.values()]
        avg_entities = sum(entity_counts) / total_docs
        docs_with_entities = sum(1 for c in entity_counts if c > 0)
        return {
            "total_documents": total_docs,
            "avg_entities_per_doc": round(avg_entities, 2),
            "documents_with_entities": docs_with_entities,
            "coverage_ratio": round(docs_with_entities / total_docs, 4),
        }

    def get_workspace_knowledge(self, workspace_id: str) -> dict:
        """Get all knowledge scoped to a workspace."""
        nodes = [n for n in self.graph._nodes.values() if n.workspace_id == workspace_id]
        public_nodes = [n for n in nodes if n.is_public]
        docs = [n for n in nodes if n.node_type == "document"]
        return {
            "workspace_id": workspace_id,
            "node_count": len(nodes),
            "document_count": len(docs),
            "public_node_count": len(public_nodes),
            "nodes": [{"id": n.id, "name": n.name, "type": n.node_type} for n in nodes[:100]],
        }

    def make_public(self, node_id: str) -> bool:
        """Mark a node as shared/public across workspaces."""
        node = self.graph._nodes.get(node_id)
        if not node:
            return False
        node.is_public = True
        self._shared_public_nodes.add(node_id)
        return True

    def visualize_graph(self, center_id: Optional[str] = None, radius: int = 1,
                         format: str = "json") -> dict:
        """Get graph data prepared for visualization."""
        if center_id:
            subgraph = self.graph.extract_subgraph(center_id, radius=radius)
        else:
            subgraph = self.graph.export_json()
            subgraph = {
                "nodes": [{"id": n["id"], "name": n["name"], "type": n["type"]}
                          for n in subgraph["nodes"]],
                "edges": [{"source": e["source"], "target": e["target"],
                           "relationship": e["relationship"], "weight": e["weight"]}
                          for e in subgraph["edges"]],
            }
        clusters = self.graph.detect_clusters()
        result = {
            "format": format,
            "graph": subgraph,
            "clusters": clusters,
            "statistics": self.graph.get_statistics(),
        }
        if format == "graphviz":
            result["dot"] = self.graph.export_graphviz()
        return result


knowledge_system = GlobalKnowledgeSystem()