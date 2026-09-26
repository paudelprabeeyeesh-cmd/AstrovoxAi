"""Search and Knowledge Management Platform — 15 high-value features.

Features
========
1.  Hybrid search with BM25 + vector fusion
2.  Cross-encoder reranker
3.  Multi-vector retrieval
4.  Incremental indexing
5.  Knowledge graph builder
6.  Citation engine
7.  OCR pipeline
8.  PDF intelligence parser
9.  Audio transcription
10. Video caption extraction
11. Chunking strategies
12. Metadata extraction
13. Semantic retrieval
14. Query understanding
15. Search analytics
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional third-party imports
# ---------------------------------------------------------------------------
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    openai = None
    HAS_OPENAI = False

try:
    from pypdf import PdfReader
    HAS_PYPDF = True
except ImportError:
    PdfReader = None
    HAS_PYPDF = False

try:
    from docx import Document as DocxDocument
    HAS_DOCX = True
except ImportError:
    DocxDocument = None
    HAS_DOCX = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    BeautifulSoup = None
    HAS_BS4 = False

try:
    import librosa
    HAS_LIBROSA = True
except ImportError:
    librosa = None
    HAS_LIBROSA = False

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    cv2 = None
    HAS_CV2 = False

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    np = None
    HAS_NUMPY = False

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    nx = None
    HAS_NETWORKX = False


# ============================================================================
# Dataclasses
# ============================================================================

@dataclass
class Document:
    """Represents an indexed document with optional multi-vector embeddings."""
    doc_id: str
    content: str
    embeddings: List[List[float]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    token_vectors: List[Tuple[str, List[float]]] = field(default_factory=list)


@dataclass
class SearchResult:
    """A single search result with provenance."""
    chunk_id: str
    document_id: str
    content: str
    score: float
    source: str = "hybrid"
    metadata: Dict[str, Any] = field(default_factory=dict)
    highlights: List[str] = field(default_factory=list)
    citation: Optional[str] = None


@dataclass
class QueryAnalysis:
    """Structured understanding of a user query."""
    original: str
    normalized: str
    intent: str
    entities: List[str]
    keywords: List[str]
    filters: Dict[str, Any]
    rewritten: str
    language: str = "en"


@dataclass
class SearchAnalyticsEvent:
    """Single search analytics event."""
    query: str
    user_id: str
    results_count: int
    clicked_index: int
    dwell_time_ms: float
    latency_ms: float
    sources: List[str]
    timestamp: str
    feedback: Optional[str] = None


@dataclass
class KnowledgeNode:
    node_id: str
    name: str
    node_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


@dataclass
class KnowledgeEdge:
    source_id: str
    target_id: str
    relation: str
    properties: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0


@dataclass
class Chunk:
    id: str
    document_id: str
    content: str
    chunk_index: int
    section: str = ""
    section_index: int = -1
    char_start: int = 0
    char_end: int = 0
    token_estimate: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


# ============================================================================
# Feature 1: Hybrid Search with BM25 + Vector Fusion
# ============================================================================

class BM25Index:
    """BM25 sparse index for keyword retrieval."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self._postings: Dict[str, Dict[str, int]] = {}
        self._doc_lengths: Dict[str, int] = {}
        self._avg_dl: float = 0.0
        self._doc_count: int = 0

    def add(self, doc_id: str, text: str) -> None:
        tokens = self._tokenize(text)
        self._doc_lengths[doc_id] = len(tokens)
        for token in tokens:
            self._postings.setdefault(token, {})[doc_id] = self._postings.get(token, {}).get(doc_id, 0) + 1

    def add_batch(self, items: List[Tuple[str, str]]) -> None:
        for doc_id, text in items:
            self.add(doc_id, text)
        self._doc_count = len(self._doc_lengths)
        self._avg_dl = sum(self._doc_lengths.values()) / max(self._doc_count, 1)

    def search(self, query: str, top_k: int = 20) -> List[Tuple[str, float]]:
        tokens = self._tokenize(query)
        scores: Dict[str, float] = defaultdict(float)
        for token in tokens:
            postings = self._postings.get(token, {})
            df = len(postings)
            idf = math.log((self._doc_count - df + 0.5) / (df + 0.5) + 1.0)
            for doc_id, tf in postings.items():
                dl = self._doc_lengths.get(doc_id, self._avg_dl or 1)
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * dl / max(self._avg_dl, 1))
                scores[doc_id] += idf * numerator / max(denominator, 1e-9)
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]

    def _tokenize(self, text: str) -> List[str]:
        return [t for t in re.findall(r"\b[a-zA-Z0-9]{2,}\b", text.lower()) if len(t) >= 2]

    @property
    def size(self) -> int:
        return self._doc_count


class VectorIndex:
    """Dense vector index with cosine similarity."""

    def __init__(self):
        self._vectors: Dict[str, List[float]] = {}

    def add(self, doc_id: str, embedding: List[float]) -> None:
        norm = math.sqrt(sum(v * v for v in embedding)) or 1.0
        self._vectors[doc_id] = [v / norm for v in embedding]

    def search(self, query_embedding: List[float], top_k: int = 20) -> List[Tuple[str, float]]:
        q_norm = math.sqrt(sum(v * v for v in query_embedding)) or 1.0
        q_vec = [v / q_norm for v in query_embedding]
        scores = []
        for doc_id, vec in self._vectors.items():
            score = sum(a * b for a, b in zip(q_vec, vec))
            scores.append((doc_id, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


class HybridSearchEngine:
    """Feature 1: Hybrid BM25 + vector fusion search with Reciprocal Rank Fusion."""

    def __init__(self, alpha: float = 0.5, fusion: str = "linear"):
        self.alpha = alpha
        self.fusion = fusion
        self.bm25 = BM25Index()
        self.vector = VectorIndex()
        self._documents: Dict[str, str] = {}

    def index(self, doc_id: str, text: str, embedding: Optional[List[float]] = None) -> None:
        self._documents[doc_id] = text
        self.bm25.add(doc_id, text)
        if embedding:
            self.vector.add(doc_id, embedding)

    def search(
        self,
        query: str,
        query_embedding: Optional[List[float]] = None,
        top_k: int = 5,
        alpha: Optional[float] = None,
    ) -> List[SearchResult]:
        alpha = alpha if alpha is not None else self.alpha
        bm25_results = dict(self.bm25.search(query, top_k=top_k * 3))
        vector_results = dict(self.vector.search(query_embedding, top_k=top_k * 3)) if query_embedding else {}

        if self.fusion == "rrf":
            return self._rrf_fusion(bm25_results, vector_results, top_k)
        return self._linear_fusion(bm25_results, vector_results, top_k, alpha)

    def _linear_fusion(self, bm25: Dict[str, float], vector: Dict[str, float],
                       top_k: int, alpha: float) -> List[SearchResult]:
        all_ids = set(bm25.keys()) | set(vector.keys())
        if not all_ids:
            return []
        max_bm25 = max(bm25.values()) if bm25 else 1.0
        max_vec = max(vector.values()) if vector else 1.0
        scores: Dict[str, float] = {}
        for doc_id in all_ids:
            b = (bm25.get(doc_id, 0.0) / max(max_bm25, 1e-9))
            v = (vector.get(doc_id, 0.0) / max(max_vec, 1e-9))
            scores[doc_id] = alpha * b + (1.0 - alpha) * v
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [SearchResult(chunk_id=doc_id, document_id=doc_id, content=self._documents.get(doc_id, ""),
                             score=score, source="hybrid") for doc_id, score in ranked if score > 0]

    def _rrf_fusion(self, bm25: Dict[str, float], vector: Dict[str, float],
                    top_k: int, k: int = 60) -> List[SearchResult]:
        scores: Dict[str, float] = defaultdict(float)
        for rank, (doc_id, _) in enumerate(sorted(bm25.items(), key=lambda x: x[1], reverse=True), 1):
            scores[doc_id] += 1.0 / (k + rank)
        for rank, (doc_id, _) in enumerate(sorted(vector.items(), key=lambda x: x[1], reverse=True), 1):
            scores[doc_id] += 1.0 / (k + rank)
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [SearchResult(chunk_id=doc_id, document_id=doc_id, content=self._documents.get(doc_id, ""),
                             score=score, source="hybrid_rrf") for doc_id, score in ranked]

    def __len__(self) -> int:
        return len(self._documents)


# ============================================================================
# Feature 2: Cross-Encoder Reranker
# ============================================================================

class CrossEncoderReranker:
    """Feature 2: Cross-encoder reranker with term overlap, BM25 boost, and position penalty."""

    def __init__(self, boost_query_term: float = 0.6, boost_exact: float = 0.3,
                 penalty_long: float = 0.05, max_length: int = 4096):
        self.boost_query_term = boost_query_term
        self.boost_exact = boost_exact
        self.penalty_long = penalty_long
        self.max_length = max_length

    def rerank(self, query: str, candidates: List[SearchResult], top_k: int = 5) -> List[SearchResult]:
        if not candidates:
            return []
        query_terms = set(self._tokenize(query))
        query_lower = query.lower()
        scored = []
        for c in candidates:
            doc_text = c.content[:self.max_length]
            doc_terms = set(self._tokenize(doc_text))
            doc_lower = doc_text.lower()

            overlap = len(query_terms & doc_terms)
            coverage = overlap / max(len(query_terms), 1)
            density = overlap / max(len(doc_terms), 1)
            exact_bonus = 2.0 if query_lower in doc_lower else 0.0
            length_penalty = max(0, len(doc_text) / max(self.max_length, 1) - 0.5) * self.penalty_long

            score = (coverage * self.boost_query_term + density * 0.2 + exact_bonus * self.boost_exact)
            score = max(0.0, score - length_penalty)
            scored.append({**c.__dict__, "score": c.score * 0.3 + score * 0.7, "rerank_score": score})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return [SearchResult(**{k: v for k, v in s.items() if k in SearchResult.__dataclass_fields__}) for s in scored[:top_k]]

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return [t for t in re.findall(r"\b[a-zA-Z0-9]{2,}\b", text.lower()) if len(t) >= 2]


# ============================================================================
# Feature 3: Multi-Vector Retrieval (colBERT-style late interaction)
# ============================================================================

class MultiVectorRetriever:
    """Feature 3: ColBERT-style multi-vector retrieval with MaxSim operator."""

    def __init__(self, max_vectors_per_doc: int = 32):
        self.max_vectors_per_doc = max_vectors_per_doc
        self._doc_vectors: Dict[str, List[List[float]]] = {}

    def index(self, doc_id: str, token_vectors: List[Tuple[str, List[float]]]) -> None:
        trimmed = token_vectors[:self.max_vectors_per_doc]
        self._doc_vectors[doc_id] = [vec for _, vec in trimmed]

    def search(self, query_vectors: List[List[float]], top_k: int = 10) -> List[Tuple[str, float]]:
        if not query_vectors or not self._doc_vectors:
            return []
        scores = []
        for doc_id, doc_vecs in self._doc_vectors.items():
            if not doc_vecs:
                continue
            max_sims = []
            for qv in query_vectors:
                best = max((sum(a * b for a, b in zip(qv, dv)) for dv in doc_vecs), default=0.0)
                max_sims.append(best)
            scores.append((doc_id, sum(max_sims) / max(len(max_sims), 1)))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


# ============================================================================
# Feature 4: Incremental Indexer
# ============================================================================

@dataclass
class IncrementalIndexState:
    """Tracks incremental indexing state for a collection."""
    collection: str
    last_sync: str
    indexed_count: int
    deleted_count: int
    pending: List[str]
    watermark: str


class IncrementalIndexer:
    """Feature 4: Incremental indexing with change tracking and watermark-based sync."""

    def __init__(self, watermark_key: str = "updated_at"):
        self.watermark_key = watermark_key
        self._indexed: Dict[str, Dict[str, Any]] = {}
        self._deleted: set = set()
        self._watermarks: Dict[str, str] = {}

    def sync(self, collection: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        last_watermark = self._watermarks.get(collection, "")
        new_items = []
        updated_count = 0
        new_count = 0
        for item in items:
            item_id = item.get("id", str(uuid.uuid4()))
            ts = item.get(self.watermark_key, "")
            is_new = item_id not in self._indexed
            if ts > last_watermark and item_id not in self._deleted:
                self._indexed[item_id] = item
                new_items.append(item)
                if is_new:
                    new_count += 1
                else:
                    updated_count += 1
        watermark = max((i.get(self.watermark_key, "") for i in items), default=last_watermark)
        self._watermarks[collection] = max(last_watermark, watermark)
        state = IncrementalIndexState(
            collection=collection,
            last_sync=datetime.now(timezone.utc).isoformat(),
            indexed_count=len(self._indexed),
            deleted_count=len(self._deleted),
            pending=[],
            watermark=self._watermarks[collection],
        )
        return {"state": state.__dict__, "new": new_count, "updated": updated_count}

    def delete(self, item_ids: List[str]) -> int:
        count = 0
        for item_id in item_ids:
            self._deleted.add(item_id)
            self._indexed.pop(item_id, None)
            count += 1
        return count

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_indexed": len(self._indexed),
            "total_deleted": len(self._deleted),
            "watermarks": dict(self._watermarks),
        }


# ============================================================================
# Feature 5: Knowledge Graph Builder
# ============================================================================

class KnowledgeGraphBuilder:
    """Feature 5: Build knowledge graphs from text with entity/relation extraction."""

    def __init__(self):
        self.nodes: Dict[str, KnowledgeNode] = {}
        self.edges: List[KnowledgeEdge] = []
        self._adjacency: Dict[str, List[str]] = defaultdict(list)
        self._edge_index: Dict[str, KnowledgeEdge] = {}

    def add_entity(self, name: str, entity_type: str, properties: Optional[Dict[str, Any]] = None) -> KnowledgeNode:
        node_id = self._node_id(name, entity_type)
        node = KnowledgeNode(node_id=node_id, name=name, node_type=entity_type, properties=properties or {})
        self.nodes[node_id] = node
        return node

    def add_relation(self, source: str, target: str, relation: str,
                     properties: Optional[Dict[str, Any]] = None) -> KnowledgeEdge:
        s_id = self._node_id(source, "entity")
        t_id = self._node_id(target, "entity")
        if s_id not in self.nodes:
            self.add_entity(source, "entity")
        if t_id not in self.nodes:
            self.add_entity(target, "entity")
        edge = KnowledgeEdge(source_id=s_id, target_id=t_id, relation=relation,
                             properties=properties or {})
        self.edges.append(edge)
        self._adjacency[s_id].append(t_id)
        self._edge_index[f"{s_id}->{relation}->{t_id}"] = edge
        return edge

    def build_from_text(self, text: str) -> Dict[str, Any]:
        entities = self._extract_entities(text)
        relations = self._extract_relations(text, entities)
        for ent in entities:
            self.add_entity(ent["name"], ent["type"], ent.get("properties"))
        for rel in relations:
            self.add_relation(rel["source"], rel["target"], rel["relation"], rel.get("properties"))
        return {"entities_added": len(entities), "relations_added": len(relations),
                "total_nodes": len(self.nodes), "total_edges": len(self.edges)}

    def subgraph(self, entity_name: str, depth: int = 2) -> Dict[str, Any]:
        node_id = self._node_id(entity_name, "entity")
        visited = {node_id}
        queue = [(node_id, 0)]
        entity_ids = {node_id}
        while queue:
            current, d = queue.pop(0)
            if d >= depth:
                continue
            for neighbor in self._adjacency.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    entity_ids.add(neighbor)
                    queue.append((neighbor, d + 1))
        nodes = [self.nodes[n] for n in entity_ids if n in self.nodes]
        edges = [e for e in self.edges if e.source_id in entity_ids or e.target_id in entity_ids]
        return {"entities": nodes, "relationships": edges}

    def shortest_path(self, source: str, target: str) -> List[str]:
        if HAS_NETWORKX:
            G = nx.DiGraph()
            for e in self.edges:
                G.add_edge(e.source_id, e.target_id, relation=e.relation)
            s_id = self._node_id(source, "entity")
            t_id = self._node_id(target, "entity")
            try:
                path = nx.shortest_path(G, s_id, t_id)
                return [self.nodes[n].name for n in path if n in self.nodes]
            except nx.NetworkXNoPath:
                return []
        visited = {self._node_id(source, "entity")}
        queue = [(self._node_id(source, "entity"), [self._node_id(source, "entity")])]
        target_id = self._node_id(target, "entity")
        while queue:
            current, path = queue.pop(0)
            if current == target_id:
                return [self.nodes.get(n, KnowledgeNode(n, n, "unknown")).name for n in path]
            for neighbor in self._adjacency.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        return []

    def to_cypher(self) -> str:
        stmts = []
        for node in self.nodes.values():
            props = ", ".join(f'{k}: {json.dumps(v)}' for k, v in node.properties.items())
            stmts.append(f"CREATE ({node.node_id}:{node.node_type} {{name: {json.dumps(node.name)}, {props}}})")
        for edge in self.edges:
            stmts.append(f"CREATE ({edge.source_id})-[:{edge.relation} {{weight: {edge.weight}}}]->({edge.target_id})")
        return ";\n".join(stmts) + ";"

    def get_stats(self) -> Dict[str, Any]:
        type_counts: Dict[str, int] = Counter(n.node_type for n in self.nodes.values())
        rel_counts: Dict[str, int] = Counter(e.relation for e in self.edges)
        return {
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "node_types": dict(type_counts),
            "relation_types": dict(rel_counts),
            "avg_degree": (sum(len(v) for v in self._adjacency.values()) / max(len(self._adjacency), 1)),
        }

    @staticmethod
    def _node_id(name: str, entity_type: str) -> str:
        return f"{entity_type}_{hashlib.md5(name.lower().encode()).hexdigest()[:12]}"

    @staticmethod
    def _extract_entities(text: str) -> List[Dict[str, Any]]:
        entities = []
        caps = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}\b", text)
        for name in set(caps):
            if len(name) < 2 or name.lower() in {"the", "and", "for", "with"}:
                continue
            entities.append({"name": name, "type": "entity", "properties": {"mentions": text.lower().count(name.lower())}})
        orgs = re.findall(r"(?:Inc|Corp|LLC|Company|Organization|University|Institute)\b", text)
        for org in set(orgs):
            entities.append({"name": org, "type": "organization"})
        dates = re.findall(r"\b(?:\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:,\s*\d{4})?)\b", text, re.I)
        for d in set(dates[:5]):
            entities.append({"name": d, "type": "date"})
        return entities[:50]

    @staticmethod
    def _extract_relations(text: str, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        relations = []
        names = [e["name"] for e in entities if e["type"] == "entity"]
        patterns = [
            (r"(?i)\b({src})\b.*?(?:is|was|are|were)\s+(?:a|an|the)?\s*(.+?)(?:\.|,|\n|$)", "is_a"),
            (r"(?i)\b({src})\b.*?(?:part of|belongs to|member of)\s+(.+?)(?:\.|,|\n|$)", "part_of"),
            (r"(?i)\b({src})\b.*?(?:created|developed|built|founded)\s+(.+?)(?:\.|,|\n|$)", "created"),
            (r"(?i)\b({src})\b.*?(?:works with|collaborates with|partners with)\s+(.+?)(?:\.|,|\n|$)", "collaborates_with"),
        ]
        for src in names[:10]:
            for pattern, rel_type in patterns:
                m = re.search(pattern.format(src=re.escape(src)), text)
                if m:
                    target = m.group(2).strip()[:100]
                    relations.append({"source": src, "target": target, "relation": rel_type})
        return relations[:20]


# ============================================================================
# Feature 6: Citation Engine
# ============================================================================

@dataclass
class Citation:
    style: str
    text: str
    authors: List[str] = field(default_factory=list)
    title: str = ""
    year: str = ""
    source: str = ""
    url: str = ""
    page: Optional[int] = None
    chunk_id: Optional[str] = None


class CitationEngine:
    """Feature 6: Citation engine with multi-style support and provenance tracking."""

    STYLES = ("apa", "mla", "chicago", "ieee", "harvard", "vancouver")

    def generate(self, document_title: str, authors: List[str], year: str = "",
                 source: str = "", url: str = "", style: str = "apa",
                 page: Optional[int] = None, chunk_id: Optional[str] = None) -> Citation:
        year = year or str(datetime.now(timezone.utc).year)
        style = style.lower() if style in self.STYLES else "apa"
        text = getattr(self, f"_format_{style}")(authors, year, document_title, source, url, page)
        return Citation(style=style, text=text, authors=authors, title=document_title,
                        year=year, source=source, url=url, page=page, chunk_id=chunk_id)

    def generate_batch(self, references: List[Dict[str, Any]], style: str = "apa") -> List[Citation]:
        return [self.generate(
            document_title=r.get("title", ""),
            authors=r.get("authors", []),
            year=r.get("year", ""),
            source=r.get("source", ""),
            url=r.get("url", ""),
            style=style,
            page=r.get("page"),
            chunk_id=r.get("chunk_id"),
        ) for r in references]

    def extract_from_chunks(self, chunks: List[Chunk]) -> List[Citation]:
        citations = []
        for chunk in chunks:
            meta = chunk.metadata or {}
            if meta.get("source_type") and chunk.content:
                citations.append(self.generate(
                    document_title=chunk.metadata.get("filename", "Unknown"),
                    authors=chunk.metadata.get("authors", []),
                    year=chunk.metadata.get("year", ""),
                    source=chunk.metadata.get("source", ""),
                    url=chunk.metadata.get("url", ""),
                    style="apa",
                    chunk_id=chunk.id,
                ))
        return citations

    def format_inline(self, citation: Citation, style: str = "apa") -> str:
        if style == "apa":
            parts = []
            if citation.authors:
                parts.append(", ".join(citation.authors[:2]) + (" et al." if len(citation.authors) > 2 else ""))
            parts.append(f"({citation.year})")
            return " ".join(parts)
        if style == "mla":
            return f"({citation.authors[0] if citation.authors else 'Unknown'} {citation.year})"
        return f"({citation.authors[0] if citation.authors else 'Unknown'}, {citation.year})"

    def to_bibliography(self, citations: List[Citation]) -> str:
        lines = []
        for i, c in enumerate(citations, 1):
            lines.append(f"[{i}] {c.text}")
        return "\n".join(lines)

    def _format_apa(self, authors, year, title, source, url, page):
        parts = [f"{', '.join(authors) if authors else 'Unknown'} ({year})." if year else f"{', '.join(authors) if authors else 'Unknown'}.",
                 f"{title}."]
        if source:
            parts.append(f"{source}.")
        if page:
            parts.append(f"p. {page}")
        if url:
            parts.append(url)
        return " ".join(parts)

    def _format_mla(self, authors, year, title, source, url, page):
        author = ", ".join(authors) if authors else "Unknown Author"
        parts = [f'{author}. "{title}."']
        if source:
            parts.append(f"{source},")
        if page:
            parts.append(f"p. {page}.")
        if url:
            parts.append(url + ".")
        parts.append(f"{datetime.now(timezone.utc).strftime('%d %b. %Y')}.")
        return " ".join(parts)

    def _format_chicago(self, authors, year, title, source, url, page):
        author = ", ".join(authors) if authors else "Unknown"
        parts = [f'{author}. "{title}."']
        if source:
            parts.append(f"{source}")
        if year:
            parts.append(f"({year}).")
        if page:
            parts.append(f"Page {page}.")
        if url:
            parts.append(url)
        return " ".join(parts)

    def _format_ieee(self, authors, title, year, source, url, page):
        author = ", ".join(authors) if authors else "Unknown"
        parts = [f'{author}, "{title},"']
        if source:
            parts.append(f"{source},")
        parts.append(f"{year}.")
        if page:
            parts.append(f"p. {page},")
        if url:
            parts.append(f"[Online]. Available: {url}.")
        return " ".join(parts)

    def _format_harvard(self, authors, year, title, source, url, page):
        author = ", ".join(authors) if authors else "Unknown"
        parts = [f"{author} ({year})"]
        parts.append(f"'{title}'")
        if source:
            parts.append(f", {source}")
        if page:
            parts.append(f", p. {page}")
        if url:
            parts.append(f". Available at: {url}")
        parts.append(".")
        return "".join(parts)

    def _format_vancouver(self, authors, title, year, source, url, page):
        author = ", ".join(authors) if authors else "Unknown"
        parts = [f"{author}. {title}."]
        if source:
            parts.append(f"{source};")
        parts.append(f"{year}.")
        if page:
            parts.append(f"p. {page}.")
        return " ".join(parts)


# ============================================================================
# Feature 7: OCR Pipeline
# ============================================================================

class OCRPipeline:
    """Feature 7: OCR pipeline with preprocessing, recognition, and post-processing."""

    def __init__(self, confidence_threshold: float = 0.5, languages: List[str] = None):
        self.confidence_threshold = confidence_threshold
        self.languages = languages or ["en"]

    def process(self, image_bytes: bytes, filename: str = "") -> Dict[str, Any]:
        start = time.time()
        preprocessed = self._preprocess(image_bytes)
        regions = self._detect_text_regions(preprocessed)
        results = []
        for region in regions:
            text, confidence = self._recognize(region)
            if confidence >= self.confidence_threshold:
                results.append({"text": text, "confidence": round(confidence, 3),
                                "bbox": region.get("bbox", [])})
        full_text = " ".join(r["text"] for r in results)
        elapsed = (time.time() - start) * 1000
        return {
            "text": full_text,
            "regions": results,
            "language": self._detect_language(full_text),
            "avg_confidence": round(sum(r["confidence"] for r in results) / max(len(results), 1), 3),
            "word_count": len(full_text.split()),
            "processing_time_ms": round(elapsed, 3),
            "engine": "simulated_heuristic",
            "note": "Production OCR requires Tesseract or cloud OCR API integration",
            "filename": filename,
        }

    def process_pdf_page(self, page_content: bytes, page_num: int = 0) -> Dict[str, Any]:
        result = self.process(page_content, filename=f"page_{page_num}")
        result["page_number"] = page_num
        return result

    def _preprocess(self, image_bytes: bytes) -> bytes:
        """Preprocess image: resize, normalize, denoise."""
        if HAS_CV2 and HAS_NUMPY:
            try:
                arr = np.frombuffer(image_bytes, np.uint8)
                img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    img = cv2.resize(img, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
                    _, img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    _, buf = cv2.imencode(".png", img)
                    return buf.tobytes()
            except Exception:
                pass
        return image_bytes

    def _detect_text_regions(self, image_bytes: bytes) -> List[Dict[str, Any]]:
        if not image_bytes:
            return []
        sample = image_bytes[:4096]
        ascii_chunks = re.findall(rb"[\x20-\x7E]{8,}", sample)
        return [{"text": chunk.decode("ascii", errors="ignore"), "bbox": [0, 0, 100, 20],
                 "bytes": chunk} for chunk in ascii_chunks[:20]]

    def _recognize(self, region: Dict[str, Any]) -> Tuple[str, float]:
        text = region.get("text", "")
        if not text:
            return "", 0.0
        readable = len(re.findall(r"[a-zA-Z]{3,}", text))
        total = len(text)
        confidence = min(1.0, readable / max(total, 1) + 0.3)
        return text, confidence

    def _detect_language(self, text: str) -> str:
        words = set(re.findall(r"\b[a-zà-ÿ]{2,}\b", text.lower()))
        if not words:
            return "en"
        return "en"


# ============================================================================
# Feature 8: PDF Intelligence Parser
# ============================================================================

class PDFIntelligenceParser:
    """Feature 8: Advanced PDF parsing with structure, tables, figures, and metadata."""

    def __init__(self):
        self.ocr = OCRPipeline()

    def parse(self, content: bytes, filename: str = "") -> Dict[str, Any]:
        start = time.time()
        if HAS_PYPDF:
            return self._parse_with_pypdf(content, filename, start)
        return self._parse_simulated(content, filename, start)

    def parse_with_structure(self, content: bytes, filename: str = "") -> Dict[str, Any]:
        result = self.parse(content, filename)
        result["sections"] = self._detect_sections(result.get("text", ""))
        result["tables"] = self._detect_tables(content)
        result["figures"] = self._detect_figures(content)
        result["references"] = self._extract_references(result.get("text", ""))
        result["key_terms"] = self._extract_key_terms(result.get("text", ""))
        return result

    def _parse_with_pypdf(self, content: bytes, filename: str, start: float) -> Dict[str, Any]:
        try:
            reader = PdfReader(BytesIO(content))
            pages_text = []
            metadata = {}
            for i, page in enumerate(reader.pages):
                t = page.extract_text() or ""
                pages_text.append(t)
                ocr_result = self.ocr.process_pdf_page(content, i)
                if ocr_result.get("text") and len(ocr_result["text"]) > len(t):
                    pages_text[i] = ocr_result["text"]
            full_text = "\n\n".join(pages_text)
            if reader.metadata:
                metadata = {
                    "title": reader.metadata.get("/Title", ""),
                    "author": reader.metadata.get("/Author", ""),
                    "subject": reader.metadata.get("/Subject", ""),
                    "creator": reader.metadata.get("/Creator", ""),
                    "producer": reader.metadata.get("/Producer", ""),
                    "creation_date": str(reader.metadata.get("/CreationDate", "")),
                }
            return {
                "text": full_text,
                "page_count": len(reader.pages),
                "metadata": metadata,
                "parse_time_ms": round((time.time() - start) * 1000, 3),
                "engine": "pypdf",
                "format": "pdf",
                "filename": filename,
            }
        except Exception as exc:
            logger.warning("pypdf parse failed: %s", exc)
            return self._parse_simulated(content, filename, start)

    def _parse_simulated(self, content: bytes, filename: str, start: float) -> Dict[str, Any]:
        text = content.decode("latin-1", errors="ignore")
        readable = re.findall(r"\(([^)]{3,})\)\s*Tj", text)
        full_text = " ".join(readable) if readable else re.sub(r"[^\x20-\x7E\n]+", " ", text)
        page_count = max(1, text.count("/Type /Page") - text.count("/Type /Pages"))
        title_match = re.search(r"/Title\s*\(([^)]+)\)", text)
        author_match = re.search(r"/Author\s*\(([^)]+)\)", text)
        metadata = {}
        if title_match:
            metadata["title"] = title_match.group(1).strip()
        if author_match:
            metadata["author"] = author_match.group(1).strip()
        return {
            "text": full_text.strip() or "[PDF content extracted]",
            "page_count": page_count,
            "metadata": metadata,
            "parse_time_ms": round((time.time() - start) * 1000, 3),
            "engine": "simulated",
            "format": "pdf",
            "filename": filename,
        }

    def _detect_sections(self, text: str) -> List[Dict[str, Any]]:
        sections = []
        for line in text.splitlines():
            m = re.match(r"^(#{1,6}\s+.*|(?:[A-Z][A-Z\s]{3,})$|\d+\.\s+[A-Z])", line.strip())
            if m:
                sections.append({"title": line.strip()[:200], "level": 1, "line": line})
        return sections[:50]

    def _detect_tables(self, content: bytes) -> List[Dict[str, Any]]:
        text = content.decode("latin-1", errors="ignore")
        rows = re.findall(r"([A-Z][a-z]+.*?)(?:\n|$)", text)
        if len(rows) > 3:
            return [{"headers": rows[0].split()[:5], "rows": [r.split()[:5] for r in rows[1:4]], "row_count": len(rows) - 1}]
        return []

    def _detect_figures(self, content: bytes) -> List[Dict[str, Any]]:
        return [{"type": "image", "count": max(1, content.count(b"/Image"))}]

    def _extract_references(self, text: str) -> List[Dict[str, Any]]:
        refs = []
        for line in text.splitlines():
            year_m = re.search(r"\b(19|20)\d{2}\b", line)
            if year_m and len(line) > 30 and ("[" in line or "(" in line):
                refs.append({"raw": line.strip()[:300], "year": year_m.group(0)})
        return refs[:30]

    def _extract_key_terms(self, text: str, top_k: int = 10) -> List[str]:
        words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
        stopwords = {"this", "that", "with", "from", "have", "been", "were", "were", "their", "would"}
        filtered = [w for w in words if w not in stopwords and len(w) >= 4]
        return [w for w, _ in Counter(filtered).most_common(top_k)]


# ============================================================================
# Feature 9: Audio Transcription
# ============================================================================

class AudioTranscriber:
    """Feature 9: Audio transcription pipeline with diarization and metadata."""

    def __init__(self, language: str = "en"):
        self.language = language

    def transcribe(self, audio_bytes: bytes, filename: str = "") -> Dict[str, Any]:
        start = time.time()
        if HAS_LIBROSA and HAS_NUMPY:
            return self._transcribe_with_librosa(audio_bytes, filename, start)
        return self._transcribe_simulated(audio_bytes, filename, start)

    def transcribe_with_timestamps(self, audio_bytes: bytes, filename: str = "") -> Dict[str, Any]:
        result = self.transcribe(audio_bytes, filename)
        result["segments"] = self._simulate_segments(result.get("text", ""))
        result["speakers"] = self._detect_speakers(result.get("text", ""))
        result["language"] = self._detect_language(result.get("text", ""))
        return result

    def _transcribe_with_librosa(self, audio_bytes: bytes, filename: str, start: float) -> Dict[str, Any]:
        try:
            y, sr = librosa.load(BytesIO(audio_bytes), sr=None, mono=True)
            duration = len(y) / sr if sr else 0.0
            rms = float(librosa.feature.rms(y=y).mean())
            text = self._audio_to_text_simulated(y, sr)
            return {
                "text": text,
                "duration_seconds": round(duration, 2),
                "sample_rate": sr,
                "rms_energy": round(rms, 4),
                "language": self.language,
                "engine": "librosa_simulated",
                "processing_time_ms": round((time.time() - start) * 1000, 3),
                "filename": filename,
                "word_count": len(text.split()),
                "segments": [],
            }
        except Exception as exc:
            logger.warning("Librosa transcription failed: %s", exc)
            return self._transcribe_simulated(audio_bytes, filename, start)

    def _transcribe_simulated(self, audio_bytes: bytes, filename: str, start: float) -> Dict[str, Any]:
        size = len(audio_bytes)
        words = max(10, min(500, size // 200))
        sample_text = "This is a simulated transcription of the audio content. " * (words // 10)
        return {
            "text": sample_text[:words * 6],
            "duration_seconds": round(size / 32000, 2),
            "sample_rate": 16000,
            "rms_energy": 0.05,
            "language": self.language,
            "engine": "simulated",
            "processing_time_ms": round((time.time() - start) * 1000, 3),
            "filename": filename,
            "word_count": words,
            "segments": [],
        }

    def _audio_to_text_simulated(self, y, sr: int) -> str:
        duration = len(y) / sr if sr else 0
        words_per_sec = 2.5
        word_count = int(duration * words_per_sec)
        base = "Transcribed audio segment with spoken content. " * (word_count // 8)
        return base[:word_count * 6] if base else "Audio transcription result."

    def _simulate_segments(self, text: str) -> List[Dict[str, Any]]:
        words = text.split()
        segments = []
        chunk_size = 20
        for i in range(0, len(words), chunk_size):
            segment_words = words[i:i + chunk_size]
            segments.append({
                "id": i // chunk_size,
                "text": " ".join(segment_words),
                "start": i * 0.5,
                "end": (i + len(segment_words)) * 0.5,
                "confidence": 0.85 + (i % 10) / 100,
            })
        return segments

    def _detect_speakers(self, text: str) -> List[Dict[str, Any]]:
        speakers = [{"id": "speaker_0", "label": "Speaker 1", "segments": 0}]
        if "?" in text or text.count(".") > 5:
            speakers.append({"id": "speaker_1", "label": "Speaker 2", "segments": 2})
        return speakers

    @staticmethod
    def _detect_language(text: str) -> str:
        return "en"


# ============================================================================
# Feature 10: Video Caption Extraction
# ============================================================================

class VideoCaptionExtractor:
    """Feature 10: Extract captions, transcripts, and frames from video files."""

    def __init__(self):
        self.audio_transcriber = AudioTranscriber()
        self.ocr = OCRPipeline()

    def extract(self, video_bytes: bytes, filename: str = "") -> Dict[str, Any]:
        start = time.time()
        audio_result = self.audio_transcriber.transcribe_with_timestamps(video_bytes, filename)
        captions = self._extract_embedded_captions(video_bytes)
        frames = self._extract_key_frames(video_bytes)
        elapsed = (time.time() - start) * 1000
        return {
            "transcript": audio_result.get("text", ""),
            "segments": audio_result.get("segments", []),
            "captions": captions,
            "key_frames": frames,
            "duration_seconds": audio_result.get("duration_seconds", 0),
            "word_count": len(audio_result.get("text", "").split()),
            "processing_time_ms": round(elapsed, 3),
            "engine": "simulated",
            "filename": filename,
            "note": "Production video processing requires ffmpeg or cloud video API",
        }

    def extract_scene_descriptions(self, video_bytes: bytes) -> List[Dict[str, Any]]:
        frames = self._extract_key_frames(video_bytes)
        descriptions = []
        for i, frame in enumerate(frames):
            desc = self.ocr.process(frame.get("content", b""), filename=f"frame_{i}")
            descriptions.append({
                "scene": i + 1,
                "timestamp": frame.get("timestamp", i * 5.0),
                "description": desc.get("text", "")[:200],
                "confidence": desc.get("avg_confidence", 0.0),
            })
        return descriptions

    def _extract_embedded_captions(self, video_bytes: bytes) -> List[Dict[str, Any]]:
        sample = video_bytes[:2048].decode("latin-1", errors="ignore")
        captions = []
        srt_pattern = re.finditer(r"(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(.+?)(?=\n\d+\n|\Z)", sample, re.DOTALL)
        for m in srt_pattern:
            captions.append({"id": m.group(1), "start": m.group(2), "end": m.group(3), "text": m.group(4).strip()})
        if not captions:
            captions.append({"id": "1", "start": "00:00:00,000", "end": "00:00:10,000", "text": "[Simulated caption]"})
        return captions

    def _extract_key_frames(self, video_bytes: bytes) -> List[Dict[str, Any]]:
        frame_count = max(1, min(10, len(video_bytes) // 50000))
        return [{"id": i, "timestamp": i * 5.0, "content": video_bytes[i * 1000:(i + 1) * 1000],
                 "size": len(video_bytes)} for i in range(frame_count)]


# ============================================================================
# Feature 11: Chunking Strategies
# ============================================================================

class ChunkingStrategies:
    """Feature 11: Multiple chunking strategies — semantic, sentence, paragraph, sliding, section, recursive."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, text: str, document_id: str, strategy: str = "semantic",
              sections: Optional[List[Dict[str, Any]]] = None) -> List[Chunk]:
        if not text or not text.strip():
            return []
        strategy = strategy.lower()
        if strategy == "section":
            return self._chunk_by_section(text, document_id, sections or [])
        if strategy == "paragraph":
            return self._chunk_by_paragraph(text, document_id)
        if strategy == "sentence":
            return self._chunk_by_sentence(text, document_id)
        if strategy == "sliding":
            return self._chunk_sliding(text, document_id)
        if strategy == "recursive":
            return self._chunk_recursive(text, document_id)
        return self._chunk_semantic(text, document_id, sections or [])

    def _chunk_by_section(self, text: str, document_id: str, sections: List[Dict[str, Any]]) -> List[Chunk]:
        if not sections:
            return self._chunk_semantic(text, document_id, [])
        lines = text.splitlines(keepends=True)
        chunks = []
        chunk_index = 0
        for idx, section in enumerate(sections):
            start = section.get("line", 0)
            end = sections[idx + 1].get("line", len(lines)) if idx + 1 < len(sections) else len(lines)
            section_text = "".join(lines[start:end]).strip()
            if not section_text:
                continue
            sub_chunks = self._chunk_semantic(section_text, document_id, [{"line": 0, "title": section.get("title", ""), "level": section.get("level", 1)}])
            for sub in sub_chunks:
                sub.section = section.get("title", "")
                sub.section_index = idx
                sub.id = self._make_id(document_id, chunk_index)
                sub.chunk_index = chunk_index
                chunks.append(sub)
                chunk_index += 1
        return chunks or self._chunk_semantic(text, document_id, [])

    def _chunk_by_paragraph(self, text: str, document_id: str) -> List[Chunk]:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks = []
        buffer: List[str] = []
        buffer_len = 0
        chunk_index = 0
        for para in paragraphs:
            if buffer_len + len(para) > self.chunk_size and buffer:
                content = "\n\n".join(buffer)
                chunks.append(Chunk(id=self._make_id(document_id, chunk_index), document_id=document_id,
                                    content=content, chunk_index=chunk_index,
                                    char_end=len(content), token_estimate=max(1, len(content.split()))))
                chunk_index += 1
                buffer = [buffer[-1]] if buffer else []
                buffer_len = sum(len(p) for p in buffer)
            buffer.append(para)
            buffer_len += len(para)
        if buffer:
            content = "\n\n".join(buffer)
            chunks.append(Chunk(id=self._make_id(document_id, chunk_index), document_id=document_id,
                                content=content, chunk_index=chunk_index,
                                char_end=len(content), token_estimate=max(1, len(content.split()))))
        return chunks

    def _chunk_by_sentence(self, text: str, document_id: str) -> List[Chunk]:
        sentences = self._split_sentences(text)
        chunks = []
        chunk_index = 0
        step = max(1, self.chunk_size // 100)
        for i in range(0, len(sentences), step):
            content = " ".join(sentences[i:i + step])
            if content.strip():
                chunk = Chunk(
                    id=self._make_id(document_id, chunk_index),
                    document_id=document_id,
                    content=content,
                    chunk_index=chunk_index,
                    char_end=len(content),
                    token_estimate=max(1, len(content.split())),
                )
                chunks.append(chunk)
                chunk_index += 1
        return chunks

    def _chunk_sliding(self, text: str, document_id: str) -> List[Chunk]:
        chunks = []
        step = max(1, self.chunk_size - self.chunk_overlap)
        for i in range(0, len(text), step):
            content = text[i:i + self.chunk_size]
            if content.strip():
                chunk = Chunk(
                    id=self._make_id(document_id, len(chunks)),
                    document_id=document_id,
                    content=content,
                    chunk_index=len(chunks),
                    char_start=i,
                    char_end=i + len(content),
                    token_estimate=max(1, len(content.split())),
                )
                chunks.append(chunk)
        return chunks

    def _chunk_recursive(self, text: str, document_id: str) -> List[Chunk]:
        separators = ["\n\n", "\n", ". ", " "]
        return self._recursive_split(text, document_id, separators, 0)

    def _recursive_split(self, text: str, document_id: str,
                         separators: List[str], depth: int) -> List[Chunk]:
        if len(text) <= self.chunk_size or depth >= len(separators):
            if text.strip():
                return [Chunk(id=self._make_id(document_id, 0), document_id=document_id,
                              content=text.strip(), chunk_index=0,
                              token_estimate=max(1, len(text.split())))]
            return []
        sep = separators[depth]
        parts = text.split(sep)
        chunks = []
        current = ""
        chunk_index = 0
        for part in parts:
            if len(current) + len(sep) + len(part) > self.chunk_size and current:
                sub = self._recursive_split(current, document_id, separators, depth + 1)
                for s in sub:
                    s.id = self._make_id(document_id, chunk_index)
                    s.chunk_index = chunk_index
                    chunks.append(s)
                    chunk_index += 1
                current = part
            else:
                current = current + sep + part if current else part
        if current.strip():
            sub = self._recursive_split(current, document_id, separators, depth + 1)
            for s in sub:
                s.id = self._make_id(document_id, chunk_index)
                s.chunk_index = chunk_index
                chunks.append(s)
                chunk_index += 1
        return chunks

    def _chunk_semantic(self, text: str, document_id: str,
                        sections: List[Dict[str, Any]]) -> List[Chunk]:
        sentences = self._split_sentences(text)
        if not sentences:
            return []
        chunks: List[Chunk] = []
        current: List[str] = []
        current_len = 0
        char_pos = 0
        chunk_index = 0
        for sentence in sentences:
            sentence_len = len(sentence)
            if current_len + sentence_len > self.chunk_size and current:
                content = " ".join(current)
                section, sidx = self._locate_section(char_pos, sections)
                chunks.append(Chunk(id=self._make_id(document_id, chunk_index), document_id=document_id,
                                    content=content, chunk_index=chunk_index, section=section,
                                    section_index=sidx, char_start=char_pos,
                                    char_end=char_pos + len(content),
                                    token_estimate=max(1, len(content.split()))))
                chunk_index += 1
                overlap = self._take_overlap(current)
                char_pos += max(0, len(content) - len(overlap))
                current = overlap
                current_len = sum(len(s) for s in current)
            current.append(sentence)
            current_len += sentence_len
        if current:
            content = " ".join(current)
            section, sidx = self._locate_section(char_pos, sections)
            chunks.append(Chunk(id=self._make_id(document_id, chunk_index), document_id=document_id,
                                content=content, chunk_index=chunk_index, section=section,
                                section_index=sidx, char_start=char_pos,
                                char_end=char_pos + len(content),
                                token_estimate=max(1, len(content.split()))))
        return chunks

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        parts = re.split(r"(?<=[.!?])\s+", text)
        return [p.strip() for p in parts if p.strip()]

    @staticmethod
    def _locate_section(char_pos: int, sections: List[Dict[str, Any]]) -> Tuple[str, int]:
        if not sections:
            return "", -1
        return sections[-1].get("title", ""), -1

    @staticmethod
    def _take_overlap(sentences: List[str]) -> List[str]:
        total = sum(len(s) for s in sentences)
        if total == 0:
            return []
        result: List[str] = []
        running = 0
        target = max(1, total // 6)
        for sentence in reversed(sentences):
            if running >= target:
                break
            result.insert(0, sentence)
            running += len(sentence)
        return result

    @staticmethod
    def _make_id(document_id: str, index: int) -> str:
        return f"{document_id}_chunk_{index}"

    def tune(self, text_length: int) -> Tuple[int, int]:
        if text_length < 2000:
            return 300, 30
        if text_length < 20000:
            return 500, 50
        if text_length < 100000:
            return 800, 100
        return 1200, 150


# ============================================================================
# Feature 12: Metadata Extractor
# ============================================================================

class MetadataExtractor:
    """Feature 12: Rich metadata extraction with entity tagging and content fingerprinting."""

    STOPWORDS = {
        "the", "and", "is", "of", "to", "in", "that", "for", "with", "as", "on",
        "at", "by", "an", "a", "be", "this", "it", "from", "or", "are", "was",
        "were", "but", "not", "have", "has", "had", "they", "their", "we", "you",
        "i", "he", "she", "his", "her", "its", "our", "your", "my", "me", "us",
        "them", "what", "which", "who", "when", "where", "why", "how", "all",
        "any", "both", "each", "few", "more", "most", "other", "some", "such",
        "than", "too", "very", "can", "will", "just", "into", "out", "up",
    }
    READING_WPM = 200

    def extract(self, text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not text:
            return {"word_count": 0, "char_count": 0}
        words = [w for w in re.findall(r"\b[a-zA-Z]+\b", text) if len(w) > 1]
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        reading_time = round(len(words) / self.READING_WPM, 2)
        language = self._detect_language(text)
        keywords = self._extract_keywords(text)
        entities = self._extract_named_entities(text)
        content_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        sentiment = self._estimate_sentiment(text)
        complexity = self._estimate_complexity(text)
        return {
            "word_count": len(words),
            "char_count": len(text),
            "sentence_count": len(sentences),
            "paragraph_count": len(paragraphs),
            "reading_time_minutes": reading_time,
            "language": language,
            "keywords": keywords,
            "entities": entities,
            "content_hash": content_hash,
            "sentiment": sentiment,
            "complexity": complexity,
            "avg_sentence_length": round(len(words) / max(len(sentences), 1), 1),
            "type_token_ratio": round(len(set(w.lower() for w in words)) / max(len(words), 1), 3),
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            **(context or {}),
        }

    def enrich_chunk_metadata(self, chunk: Chunk, document_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        meta = self.extract(chunk.content, context={"chunk_id": chunk.id, "document_id": chunk.document_id,
                                                    "chunk_index": chunk.chunk_index, "section": chunk.section})
        if chunk.metadata:
            meta.update(chunk.metadata)
        if document_metadata:
            meta["document_metadata"] = document_metadata
        chunk.metadata = meta
        return meta

    @staticmethod
    def _detect_language(text: str) -> str:
        words = set(re.findall(r"\b[a-zà-ÿ]{2,}\b", text.lower()))
        if not words:
            return "en"
        lang_keywords = {
            "en": {"the", "and", "is", "of", "to", "in"},
            "es": {"el", "la", "de", "que", "y"},
            "fr": {"le", "de", "un", "une", "et"},
            "de": {"der", "die", "das", "und", "ist"},
            "it": {"il", "di", "che", "è", "un"},
            "pt": {"o", "a", "de", "que", "e"},
        }
        scores = {lang: len(words & kw) for lang, kw in lang_keywords.items()}
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "en"

    def _extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
        filtered = [w for w in words if w not in self.STOPWORDS and len(w) >= 4]
        return [w for w, _ in Counter(filtered).most_common(max_keywords)]

    def _extract_named_entities(self, text: str) -> List[Dict[str, str]]:
        entities = []
        caps = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\b", text)
        for name in set(caps):
            if len(name) >= 3 and name.lower() not in self.STOPWORDS:
                entities.append({"name": name, "type": "PERSON_OR_ORG"})
        emails = re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text)
        for email in set(emails):
            entities.append({"name": email, "type": "EMAIL"})
        return entities[:20]

    @staticmethod
    def _estimate_sentiment(text: str) -> str:
        positive = {"good", "great", "excellent", "amazing", "wonderful", "positive", "love", "best"}
        negative = {"bad", "terrible", "awful", "poor", "negative", "hate", "worst", "fail"}
        words = set(re.findall(r"\b[a-z]+\b", text.lower()))
        pos = len(words & positive)
        neg = len(words & negative)
        if pos > neg:
            return "positive"
        if neg > pos:
            return "negative"
        return "neutral"

    @staticmethod
    def _estimate_complexity(text: str) -> str:
        words = text.split()
        if not words:
            return "simple"
        avg_len = sum(len(w) for w in words) / len(words)
        if avg_len > 7:
            return "complex"
        if avg_len > 5:
            return "moderate"
        return "simple"


# ============================================================================
# Feature 13: Semantic Retriever
# ============================================================================

class SemanticRetriever:
    """Feature 13: Semantic retrieval with embedding-based similarity and contextual reranking."""

    def __init__(self, embedding_fn=None):
        self.embedding_fn = embedding_fn or self._default_embed
        self._documents: Dict[str, Document] = {}
        self._index: Dict[str, List[float]] = {}

    def index(self, doc: Document) -> None:
        self._documents[doc.doc_id] = doc
        if doc.embeddings:
            primary = doc.embeddings[0]
            norm = math.sqrt(sum(v * v for v in primary)) or 1.0
            self._index[doc.doc_id] = [v / norm for v in primary]

    def index_batch(self, documents: List[Document]) -> None:
        for doc in documents:
            self.index(doc)

    def retrieve(self, query: str, top_k: int = 5, min_score: float = 0.0) -> List[SearchResult]:
        if not self._index:
            return []
        query_vec = self.embedding_fn(query)
        q_norm = math.sqrt(sum(v * v for v in query_vec)) or 1.0
        q_vec = [v / q_norm for v in query_vec]
        scores = []
        for doc_id, vec in self._index.items():
            score = sum(a * b for a, b in zip(q_vec, vec))
            if score >= min_score:
                scores.append((doc_id, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return [SearchResult(chunk_id=doc_id, document_id=doc_id,
                             content=self._documents[doc_id].content, score=score, source="semantic")
                for doc_id, score in scores[:top_k]]

    def retrieve_with_context(self, query: str, context_docs: List[str], top_k: int = 5) -> List[SearchResult]:
        expanded_query = query + " " + " ".join(context_docs[:3])
        return self.retrieve(expanded_query, top_k)

    def _default_embed(self, text: str) -> List[float]:
        vec = [0.0] * 384
        words = re.findall(r"\b[a-zA-Z]{2,}\b", text.lower())
        for i, word in enumerate(words[:384]):
            vec[i % 384] += hash(word) % 100 / 100.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


# ============================================================================
# Feature 14: Query Understanding
# ============================================================================

class QueryUnderstanding:
    """Feature 14: Query understanding with intent classification, entity extraction, and query rewriting."""

    INTENT_PATTERNS = {
        "search": [r"(?i)\b(find|search|look\s+for|get|show|list)\b"],
        "summarize": [r"(?i)\b(summarize|summary|summarise|brief|overview|tldr|tl;?dr)\b"],
        "compare": [r"(?i)\b(compare|comparison|difference|versus|vs\.?)\b"],
        "analyze": [r"(?i)\b(analyze|analyse|analysis|examine|break\s+down)\b"],
        "explain": [r"(?i)\b(explain|what\s+is|how\s+does|describe|tell\s+me)\b"],
        "generate": [r"(?i)\b(generate|create|write|compose|draft|produce)\b"],
        "translate": [r"(?i)\b(translate|translation|in\s+(?:english|spanish|french|german|chinese))\b"],
        "code": [r"(?i)\b(code|function|implement|script|program|debug)\b"],
    }

    LANGUAGE_PATTERNS = {
        "es": [r"(?i)\b(qué|cómo|dónde|cuándo|por\s+qué|buscar|encontrar|ayuda)\b"],
        "fr": [r"(?i)\b(qu'est-ce\s+que|comment|où|pourquoi|chercher|trouver)\b"],
        "de": [r"(?i)\b(was|wie|wo|warum|suchen|finden)\b"],
        "zh": [r"[\u4e00-\u9fff]"],
    }

    def analyze(self, query: str) -> QueryAnalysis:
        normalized = self._normalize(query)
        intent = self._classify_intent(normalized)
        entities = self._extract_entities(normalized)
        keywords = self._extract_keywords(normalized)
        filters = self._extract_filters(normalized)
        rewritten = self._rewrite(query, intent, entities, keywords)
        language = self._detect_language(query)
        return QueryAnalysis(original=query, normalized=normalized, intent=intent,
                             entities=entities, keywords=keywords, filters=filters,
                             rewritten=rewritten, language=language)

    def rewrite_for_retrieval(self, query_analysis: QueryAnalysis) -> str:
        parts = [query_analysis.normalized]
        if query_analysis.keywords:
            parts.append(" ".join(query_analysis.keywords[:5]))
        if query_analysis.entities:
            parts.append(" ".join(query_analysis.entities[:3]))
        return " ".join(parts)

    def expand(self, query: str) -> List[str]:
        analysis = self.analyze(query)
        expansions = [query, analysis.rewritten]
        synonyms = self._get_synonyms(analysis.keywords)
        for syn in synonyms[:5]:
            expansions.append(f"{query} {syn}")
        return list(dict.fromkeys(expansions))

    def _normalize(self, query: str) -> str:
        return re.sub(r"\s+", " ", query.strip().lower())

    def _classify_intent(self, query: str) -> str:
        scores = {}
        for intent, patterns in self.INTENT_PATTERNS.items():
            scores[intent] = sum(1 for p in patterns if re.search(p, query))
        if not scores or max(scores.values()) == 0:
            return "search"
        return max(scores, key=scores.get)

    def _extract_entities(self, query: str) -> List[str]:
        entities = []
        caps = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\b", query)
        entities.extend([e for e in caps if len(e) >= 2])
        quoted = re.findall(r'"([^"]+)"|\'([^\']+)\'', query)
        entities.extend(q[0] or q[1] for q in quoted)
        numbers = re.findall(r"\b\d{4}\b", query)
        entities.extend(numbers)
        return list(dict.fromkeys(entities))

    def _extract_keywords(self, query: str) -> List[str]:
        words = re.findall(r"\b[a-zA-Z]{3,}\b", query.lower())
        stopwords = {"the", "and", "is", "of", "to", "in", "that", "for", "with", "as", "on",
                     "at", "by", "an", "a", "be", "this", "it", "from", "or", "are", "was"}
        return [w for w in words if w not in stopwords][:10]

    def _extract_filters(self, query: str) -> Dict[str, Any]:
        filters = {}
        date_match = re.search(r"(?i)(?:from|since|after|before)\s+(\d{4}|\w+\s+\d{4})", query)
        if date_match:
            filters["date"] = date_match.group(1)
        type_match = re.search(r"(?i)type:\s*(\w+)", query)
        if type_match:
            filters["type"] = type_match.group(1)
        author_match = re.search(r"(?i)(?:by|author)\s*:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", query)
        if author_match:
            filters["author"] = author_match.group(1)
        return filters

    def _rewrite(self, query: str, intent: str, entities: List[str], keywords: List[str]) -> str:
        rewritten = query
        if intent == "search":
            rewritten = f"find information about {' '.join(keywords[:3])}"
        elif intent == "summarize":
            rewritten = f"provide a summary of {' '.join(keywords[:3])}"
        elif intent == "compare":
            rewritten = f"compare and contrast {' and '.join(keywords[:2])}"
        if entities:
            rewritten += f" related to {' '.join(entities[:2])}"
        return rewritten

    def _detect_language(self, query: str) -> str:
        for lang, patterns in self.LANGUAGE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query):
                    return lang
        return "en"

    @staticmethod
    def _get_synonyms(keywords: List[str]) -> List[str]:
        synonym_map = {
            "search": ["find", "lookup", "retrieve"],
            "create": ["build", "generate", "make", "produce"],
            "analyze": ["examine", "review", "inspect"],
            "help": ["assist", "support", "guide"],
            "error": ["bug", "issue", "problem", "fault"],
            "data": ["information", "content", "records"],
            "model": ["system", "framework", "architecture"],
            "fast": ["quick", "rapid", "speedy"],
            "good": ["great", "excellent", "quality"],
        }
        result = []
        for kw in keywords[:5]:
            result.extend(synonym_map.get(kw.lower(), []))
        return result


# ============================================================================
# Feature 15: Search Analytics
# ============================================================================

class SearchAnalytics:
    """Feature 15: Search analytics with metrics, trends, and feedback tracking."""

    def __init__(self):
        self._events: List[SearchAnalyticsEvent] = []
        self._query_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "count": 0, "total_latency": 0.0, "total_dwell": 0.0,
            "clicks": defaultdict(int), "zero_result_count": 0,
            "sources_used": Counter(),
        })
        self._user_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total_queries": 0, "avg_latency": 0.0, "total_dwell": 0.0,
            "feedback_positive": 0, "feedback_negative": 0,
        })

    def record(self, event: SearchAnalyticsEvent) -> None:
        self._events.append(event)
        qs = self._query_stats[event.query]
        qs["count"] += 1
        qs["total_latency"] += event.latency_ms
        qs["total_dwell"] += event.dwell_time_ms
        qs["clicks"][event.clicked_index] += 1
        if event.results_count == 0:
            qs["zero_result_count"] += 1
        for src in event.sources:
            qs["sources_used"][src] += 1
        us = self._user_stats[event.user_id]
        us["total_queries"] += 1
        us["avg_latency"] = (us["avg_latency"] * (us["total_queries"] - 1) + event.latency_ms) / us["total_queries"]
        us["total_dwell"] += event.dwell_time_ms
        if event.feedback == "positive":
            us["feedback_positive"] += 1
        if event.feedback == "negative":
            us["feedback_negative"] += 1

    def get_query_stats(self, query: str) -> Dict[str, Any]:
        qs = self._query_stats.get(query, {})
        if not qs:
            return {}
        return {
            "query": query,
            "total_queries": qs["count"],
            "avg_latency_ms": round(qs["total_latency"] / max(qs["count"], 1), 2),
            "avg_dwell_ms": round(qs["total_dwell"] / max(qs["count"], 1), 2),
            "zero_result_rate": round(qs["zero_result_count"] / max(qs["count"], 1), 3),
            "click_distribution": dict(qs["clicks"]),
            "sources": dict(qs["sources_used"]),
        }

    def get_trending_queries(self, limit: int = 20) -> List[Dict[str, Any]]:
        trending = sorted(self._query_stats.items(), key=lambda x: x[1]["count"], reverse=True)[:limit]
        return [{"query": q, **self.get_query_stats(q)} for q, _ in trending]

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        us = self._user_stats.get(user_id, {})
        if not us:
            return {"user_id": user_id, "total_queries": 0}
        return {
            "user_id": user_id,
            "total_queries": us["total_queries"],
            "avg_latency_ms": round(us["avg_latency"], 2),
            "total_dwell_ms": round(us["total_dwell"], 2),
            "positive_feedback": us["feedback_positive"],
            "negative_feedback": us["feedback_negative"],
            "satisfaction_rate": round(us["feedback_positive"] / max(us["feedback_positive"] + us["feedback_negative"], 1), 3),
        }

    def get_overall_metrics(self) -> Dict[str, Any]:
        total = len(self._events)
        if total == 0:
            return {"total_events": 0}
        avg_latency = sum(e.latency_ms for e in self._events) / total
        avg_dwell = sum(e.dwell_time_ms for e in self._events) / total
        zero_rate = sum(1 for e in self._events if e.results_count == 0) / total
        source_dist = Counter()
        for e in self._events:
            for s in e.sources:
                source_dist[s] += 1
        return {
            "total_events": total,
            "avg_latency_ms": round(avg_latency, 2),
            "avg_dwell_ms": round(avg_dwell, 2),
            "zero_result_rate": round(zero_rate, 3),
            "source_distribution": dict(source_dist),
            "unique_queries": len(self._query_stats),
            "unique_users": len(self._user_stats),
        }

    def get_insights(self) -> List[Dict[str, Any]]:
        insights = []
        for query, stats in sorted(self._query_stats.items(), key=lambda x: x[1]["count"], reverse=True)[:20]:
            if stats["zero_result_count"] / max(stats["count"], 1) > 0.3:
                insights.append({"type": "zero_result_risk", "query": query,
                                 "zero_rate": round(stats["zero_result_count"] / max(stats["count"], 1), 3),
                                 "suggestion": "Consider adding related documents or improving query expansion"})
            if stats["total_latency"] / max(stats["count"], 1) > 500:
                insights.append({"type": "slow_query", "query": query,
                                 "avg_latency": round(stats["total_latency"] / stats["count"], 1),
                                 "suggestion": "Consider caching or optimizing retrieval for this query"})
        return insights[:10]


# ============================================================================
# Orchestrator: Unified Search and Knowledge Platform
# ============================================================================

class SearchKnowledgePlatform:
    """Orchestrates all 15 search, RAG, and knowledge management features."""

    def __init__(self, embedding_fn=None):
        self.hybrid = HybridSearchEngine()
        self.reranker = CrossEncoderReranker()
        self.multi_vector = MultiVectorRetriever()
        self.incremental = IncrementalIndexer()
        self.graph_builder = KnowledgeGraphBuilder()
        self.citation = CitationEngine()
        self.ocr = OCRPipeline()
        self.pdf_parser = PDFIntelligenceParser()
        self.audio = AudioTranscriber()
        self.video = VideoCaptionExtractor()
        self.chunker = ChunkingStrategies()
        self.metadata = MetadataExtractor()
        self.semantic = SemanticRetriever(embedding_fn)
        self.query_understanding = QueryUnderstanding()
        self.analytics = SearchAnalytics()

    # -- Feature 1: Hybrid Search --
    def hybrid_search(self, query: str, query_embedding: Optional[List[float]] = None,
                      top_k: int = 5, alpha: float = 0.5) -> List[SearchResult]:
        results = self.hybrid.search(query, query_embedding, top_k, alpha)
        self.analytics.record(SearchAnalyticsEvent(
            query=query, user_id="system", results_count=len(results),
            clicked_index=0, dwell_time_ms=0.0, latency_ms=0.0,
            sources=["hybrid"], timestamp=datetime.now(timezone.utc).isoformat(),
        ))
        return results

    # -- Feature 2: Reranking --
    def rerank(self, query: str, candidates: List[SearchResult], top_k: int = 5) -> List[SearchResult]:
        return self.reranker.rerank(query, candidates, top_k)

    # -- Feature 3: Multi-vector retrieval --
    def multi_vector_search(self, query_vectors: List[List[float]], top_k: int = 5) -> List[Tuple[str, float]]:
        return self.multi_vector.search(query_vectors, top_k)

    # -- Feature 4: Incremental indexing --
    def incremental_sync(self, collection: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self.incremental.sync(collection, items)

    def incremental_delete(self, item_ids: List[str]) -> int:
        return self.incremental.delete(item_ids)

    # -- Feature 5: Knowledge graph --
    def build_graph_from_text(self, text: str) -> Dict[str, Any]:
        return self.graph_builder.build_from_text(text)

    def graph_subgraph(self, entity: str, depth: int = 2) -> Dict[str, Any]:
        return self.graph_builder.subgraph(entity, depth)

    def graph_shortest_path(self, source: str, target: str) -> List[str]:
        return self.graph_builder.shortest_path(source, target)

    # -- Feature 6: Citation --
    def generate_citation(self, title: str, authors: List[str], style: str = "apa", **kwargs) -> Citation:
        return self.citation.generate(title, authors, style=style, **kwargs)

    def citations_from_chunks(self, chunks: List[Chunk]) -> List[Citation]:
        return self.citation.extract_from_chunks(chunks)

    # -- Feature 7: OCR --
    def ocr_process(self, image_bytes: bytes, filename: str = "") -> Dict[str, Any]:
        return self.ocr.process(image_bytes, filename)

    # -- Feature 8: PDF intelligence --
    def parse_pdf(self, content: bytes, filename: str = "", with_structure: bool = False) -> Dict[str, Any]:
        if with_structure:
            return self.pdf_parser.parse_with_structure(content, filename)
        return self.pdf_parser.parse(content, filename)

    # -- Feature 9: Audio transcription --
    def transcribe_audio(self, audio_bytes: bytes, filename: str = "",
                         with_segments: bool = False) -> Dict[str, Any]:
        if with_segments:
            return self.audio.transcribe_with_timestamps(audio_bytes, filename)
        return self.audio.transcribe(audio_bytes, filename)

    # -- Feature 10: Video captions --
    def extract_video_captions(self, video_bytes: bytes, filename: str = "",
                               with_scenes: bool = False) -> Dict[str, Any]:
        if with_scenes:
            return {"captions": self.video.extract(video_bytes, filename),
                    "scenes": self.video.extract_scene_descriptions(video_bytes)}
        return self.video.extract(video_bytes, filename)

    # -- Feature 11: Chunking --
    def chunk_document(self, text: str, document_id: str, strategy: str = "semantic",
                       chunk_size: int = 500, chunk_overlap: int = 50,
                       sections: Optional[List[Dict[str, Any]]] = None) -> List[Chunk]:
        self.chunker.chunk_size = chunk_size
        self.chunker.chunk_overlap = chunk_overlap
        return self.chunker.chunk(text, document_id, strategy, sections)

    # -- Feature 12: Metadata extraction --
    def extract_metadata(self, text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.metadata.extract(text, context)

    def enrich_chunks(self, chunks: List[Chunk],
                      document_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return [self.metadata.enrich_chunk_metadata(c, document_metadata) for c in chunks]

    # -- Feature 13: Semantic retrieval --
    def semantic_search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        return self.semantic.retrieve(query, top_k)

    def index_semantic_documents(self, documents: List[Document]) -> None:
        self.semantic.index_batch(documents)

    # -- Feature 14: Query understanding --
    def understand_query(self, query: str) -> QueryAnalysis:
        return self.query_understanding.analyze(query)

    def expand_query(self, query: str) -> List[str]:
        return self.query_understanding.expand(query)

    # -- Feature 15: Search analytics --
    def record_search_event(self, query: str, user_id: str, results_count: int,
                            latency_ms: float, sources: List[str],
                            clicked_index: int = 0, dwell_time_ms: float = 0.0,
                            feedback: Optional[str] = None) -> None:
        self.analytics.record(SearchAnalyticsEvent(
            query=query, user_id=user_id, results_count=results_count,
            clicked_index=clicked_index, dwell_time_ms=dwell_time_ms,
            latency_ms=latency_ms, sources=sources,
            timestamp=datetime.now(timezone.utc).isoformat(), feedback=feedback,
        ))

    def get_search_insights(self) -> Dict[str, Any]:
        return {
            "overall": self.analytics.get_overall_metrics(),
            "trending": self.analytics.get_trending_queries(20),
            "insights": self.analytics.get_insights(),
        }

    # -- Unified search pipeline --
    def search_pipeline(self, query: str, user_id: str = "system", top_k: int = 5,
                        strategy: str = "hybrid") -> Dict[str, Any]:
        start = time.time()
        analysis = self.understand_query(query)
        expanded = self.expand_query(query) if strategy in {"hybrid", "semantic"} else [query]
        candidates: List[SearchResult] = []
        sources: List[str] = []
        if strategy in {"hybrid", "auto"}:
            candidates = self.hybrid_search(query, top_k=top_k * 2)
            sources.append("hybrid")
        if strategy in {"semantic", "auto"}:
            semantic_results = self.semantic_search(query, top_k=top_k * 2)
            candidates.extend(semantic_results)
            sources.append("semantic")
        if not candidates:
            candidates = [SearchResult(chunk_id="empty", document_id="empty", content="", score=0.0)]
        reranked = self.rerank(query, candidates, top_k=top_k)
        latency = (time.time() - start) * 1000
        self.record_search_event(query=query, user_id=user_id, results_count=len(reranked),
                                 latency_ms=latency, sources=sources)
        return {
            "query": query,
            "analysis": analysis.__dict__,
            "results": [r.__dict__ for r in reranked],
            "sources": sources,
            "latency_ms": round(latency, 2),
            "result_count": len(reranked),
        }
