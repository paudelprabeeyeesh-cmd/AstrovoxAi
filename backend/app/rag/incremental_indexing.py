"""Incremental indexing for RAG pipelines with deduplication and live updates."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class IndexedDocument:
    doc_id: str
    text: str
    hash: str
    indexed_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class IncrementalIndexer:
    """Incremental indexing with deduplication, update detection, and batch processing."""

    def __init__(self, batch_size: int = 100, deduplicate: bool = True):
        self.batch_size = batch_size
        self.deduplicate = deduplicate
        self.documents: Dict[str, IndexedDocument] = {}
        self.seen_hashes: set = set()
        self.last_indexed: Optional[datetime] = None
        self.stats: Dict[str, int] = {"indexed": 0, "updated": 0, "skipped": 0, "deleted": 0}

    def compute_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def add_documents(self, documents: List[Dict[str, Any]]) -> Tuple[int, int]:
        new_docs = 0
        skipped = 0
        for doc in documents:
            text = doc.get("text", "")
            doc_hash = self.compute_hash(text)
            if self.deduplicate and doc_hash in self.seen_hashes:
                skipped += 1
                continue
            doc_id = doc.get("id", str(len(self.documents)))
            if doc_id in self.documents:
                self.stats["updated"] += 1
            else:
                self.stats["indexed"] += 1
                new_docs += 1
            self.documents[doc_id] = IndexedDocument(
                doc_id=doc_id,
                text=text,
                hash=doc_hash,
                indexed_at=datetime.now().isoformat(),
                metadata=doc.get("metadata", {}),
            )
            self.seen_hashes.add(doc_hash)
        self.last_indexed = datetime.now()
        return new_docs, skipped

    def delete_document(self, doc_id: str) -> bool:
        if doc_id in self.documents:
            del self.documents[doc_id]
            self.stats["deleted"] += 1
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        return {
            **self.stats,
            "total_documents": len(self.documents),
            "total_hashes": len(self.seen_hashes),
            "last_indexed": self.last_indexed.isoformat() if self.last_indexed else None,
        }

    def get_documents(self) -> List[Dict[str, Any]]:
        return [{"doc_id": d.doc_id, "text": d.text, "hash": d.hash, "indexed_at": d.indexed_at, "metadata": d.metadata} for d in self.documents.values()]

    def get_changes_since(self, since: datetime) -> List[IndexedDocument]:
        if not self.last_indexed:
            return []
        return [d for d in self.documents.values() if datetime.fromisoformat(d.indexed_at) >= since]
