"""Document processing for knowledge ingestion."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ProcessedDocument:
    document_id: str
    title: str
    content: str
    chunks: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    processed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class DocumentProcessor:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._documents: Dict[str, ProcessedDocument] = {}

    def process(self, title: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> ProcessedDocument:
        chunks = self._chunk(content)
        doc = ProcessedDocument(
            document_id=uuid.uuid4().hex,
            title=title,
            content=content,
            chunks=chunks,
            metadata=metadata or {},
        )
        self._documents[doc.document_id] = doc
        return doc

    def _chunk(self, content: str) -> List[str]:
        chunks = []
        start = 0
        while start < len(content):
            end = start + self.chunk_size
            chunks.append(content[start:end])
            start = end - self.chunk_overlap
        return chunks

    def get_document(self, document_id: str) -> Optional[ProcessedDocument]:
        return self._documents.get(document_id)


document_processor = DocumentProcessor()
