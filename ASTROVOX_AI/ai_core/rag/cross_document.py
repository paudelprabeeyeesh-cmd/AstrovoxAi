"""Cross-document reasoning for RAG pipelines."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class DocumentRelation:
    source_doc_id: str
    target_doc_id: str
    relation_type: str
    score: float
    evidence: str = ""


class CrossDocumentReasoner:
    """Cross-document reasoning to connect and reason across multiple retrieved documents."""

    def __init__(self, similarity_threshold: float = 0.3):
        self.similarity_threshold = similarity_threshold
        self._document_index: Dict[str, str] = {}
        self._relations: List[DocumentRelation] = []

    def index_documents(self, documents: List[Dict[str, Any]]) -> None:
        for doc in documents:
            doc_id = doc.get("id", doc.get("chunk_id", ""))
            content = doc.get("content", "")
            if doc_id:
                self._document_index[doc_id] = content

    def build_relations(self, documents: List[Dict[str, Any]]) -> List[DocumentRelation]:
        self._relations = []
        doc_ids = [doc.get("id", doc.get("chunk_id", "")) for doc in documents]
        contents = [doc.get("content", "") for doc in documents]
        for i in range(len(documents)):
            for j in range(i + 1, len(documents)):
                score = self._semantic_similarity(contents[i], contents[j])
                if score >= self.similarity_threshold:
                    relation_type = self._classify_relation(contents[i], contents[j])
                    self._relations.append(DocumentRelation(
                        source_doc_id=doc_ids[i],
                        target_doc_id=doc_ids[j],
                        relation_type=relation_type,
                        score=score,
                        evidence=f"Similarity score: {score:.3f}",
                    ))
        self._relations.sort(key=lambda r: r.score, reverse=True)
        return self._relations

    def reason(self, query: str, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        self.index_documents(documents)
        relations = self.build_relations(documents)
        grouped = self._group_by_relation_type(relations)
        summary = self._generate_summary(query, documents, relations)
        return {
            "query": query,
            "document_count": len(documents),
            "relations_found": len(relations),
            "grouped_relations": grouped,
            "summary": summary,
            "supporting_documents": [r.source_doc_id for r in relations[:5]],
        }

    def _semantic_similarity(self, text_a: str, text_b: str) -> float:
        words_a = set(text_a.lower().split())
        words_b = set(text_b.lower().split())
        if not words_a or not words_b:
            return 0.0
        overlap = len(words_a & words_b)
        return overlap / max(len(words_a | words_b), 1)

    def _classify_relation(self, text_a: str, text_b: str) -> str:
        words_a = set(text_a.lower().split())
        words_b = set(text_b.lower().split())
        shared = words_a & words_b
        if len(shared) > len(words_a) * 0.5 or len(shared) > len(words_b) * 0.5:
            return "supports"
        if len(shared) > 0:
            return "related"
        return "contrasting"

    def _group_by_relation_type(self, relations: List[DocumentRelation]) -> Dict[str, List[str]]:
        grouped: Dict[str, List[str]] = {}
        for rel in relations:
            grouped.setdefault(rel.relation_type, []).append(rel.target_doc_id)
        return grouped

    def _generate_summary(self, query: str, documents: List[Dict[str, Any]], relations: List[DocumentRelation]) -> str:
        if not documents:
            return ""
        parts = [f"Query: {query}", f"Documents analyzed: {len(documents)}", f"Cross-document relations: {len(relations)}"]
        for rel in relations[:3]:
            parts.append(f"- {rel.source_doc_id} -> {rel.target_doc_id} ({rel.relation_type}, score={rel.score:.3f})")
        return "\n".join(parts)
