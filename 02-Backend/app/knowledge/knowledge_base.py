"""
Knowledge Base - Centralized knowledge repository.

Integrates:
- Structured knowledge graph entities
- Unstructured document chunks
- Embeddings for semantic search
- Metadata and provenance tracking
"""

from typing import Any, Dict, List, Optional


class KnowledgeBase:
    """Centralized knowledge repository."""

    def __init__(self):
        self._entities: Dict[str, Dict[str, Any]] = {}
        self._documents: Dict[str, Dict[str, Any]] = {}
        self._next_doc_id = 1

    def add_entity(self, entity_type: str, name: str, properties: Optional[Dict[str, Any]] = None) -> str:
        entity_id = f"entity_{len(self._entities) + 1}"
        self._entities[entity_id] = {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "name": name,
            "properties": properties or {},
            "created_at": __import__("datetime").datetime.utcnow().isoformat(),
        }
        return entity_id

    def add_document(self, user_id: str, title: str, content: str, doc_type: str = "text", metadata: Optional[Dict[str, Any]] = None) -> str:
        doc_id = f"kb_doc_{self._next_doc_id}"
        self._next_doc_id += 1
        self._documents[doc_id] = {
            "doc_id": doc_id,
            "user_id": user_id,
            "title": title,
            "content": content,
            "doc_type": doc_type,
            "metadata": metadata or {},
            "created_at": __import__("datetime").datetime.utcnow().isoformat(),
        }
        return doc_id

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        return self._documents.get(doc_id)

    def list_documents(self, user_id: str, doc_type: Optional[str] = None) -> List[Dict[str, Any]]:
        results = []
        for doc in self._documents.values():
            if doc.get("user_id") != user_id:
                continue
            if doc_type and doc.get("doc_type") != doc_type:
                continue
            results.append(doc)
        results.sort(key=lambda d: d.get("created_at", ""), reverse=True)
        return results

    def search(self, query: str, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        query_lower = query.lower()
        results = []
        for doc in self._documents.values():
            if doc.get("user_id") != user_id:
                continue
            title = doc.get("title", "").lower()
            content = doc.get("content", "").lower()
            if query_lower in title or query_lower in content:
                score = 0.0
                if query_lower in title:
                    score += 0.5
                if query_lower in content:
                    score += 0.3
                results.append({**doc, "search_score": score})
        results.sort(key=lambda r: r.get("search_score", 0.0), reverse=True)
        return results[:limit]

    def delete_document(self, doc_id: str) -> bool:
        return self._documents.pop(doc_id, None) is not None

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_entities": len(self._entities),
            "total_documents": len(self._documents),
        }
