"""RAG Knowledge Base — document upload, chunking, and semantic search."""

import os
import re
import logging
import hashlib
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime

from .embeddings import embedding_service
from .providers.base import EmbeddingVector

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """A chunk of a document."""
    id: str
    document_id: str
    content: str
    chunk_index: int
    metadata: dict = field(default_factory=dict)
    embedding: Optional[list[float]] = None


@dataclass
class Document:
    """An uploaded document."""
    id: str
    user_id: str
    filename: str
    file_type: str
    content: str
    chunk_count: int = 0
    created_at: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class SearchResult:
    """A search result from the knowledge base."""
    chunk: DocumentChunk
    score: float
    document: Optional[Document] = None


class TextChunker:
    """Split text into chunks for embedding."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str, document_id: str) -> list[DocumentChunk]:
        """Split text into overlapping chunks."""
        if not text.strip():
            return []

        chunks = []
        sentences = re.split(r'(?<=[.!?])\s+', text)

        current_chunk = ""
        chunk_index = 0

        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= self.chunk_size:
                current_chunk += " " + sentence if current_chunk else sentence
            else:
                if current_chunk.strip():
                    chunks.append(DocumentChunk(
                        id=f"{document_id}_chunk_{chunk_index}",
                        document_id=document_id,
                        content=current_chunk.strip(),
                        chunk_index=chunk_index,
                    ))
                    chunk_index += 1

                words = current_chunk.split()
                overlap_words = words[-self.chunk_overlap:] if len(words) > self.chunk_overlap else []
                current_chunk = " ".join(overlap_words + sentence.split())

        if current_chunk.strip():
            chunks.append(DocumentChunk(
                id=f"{document_id}_chunk_{chunk_index}",
                document_id=document_id,
                content=current_chunk.strip(),
                chunk_index=chunk_index,
            ))

        return chunks


class KnowledgeBase:
    """RAG knowledge base with document storage and semantic search."""

    def __init__(self):
        self._documents: dict[str, Document] = {}
        self._chunks: dict[str, DocumentChunk] = {}
        self._user_documents: dict[str, list[str]] = {}
        self._chunker = TextChunker()

    def _generate_id(self, user_id: str, filename: str) -> str:
        """Generate a unique document ID."""
        content = f"{user_id}_{filename}_{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()

    async def upload_document(
        self,
        user_id: str,
        filename: str,
        content: str,
        file_type: str = "text",
    ) -> Optional[Document]:
        """Upload and process a document."""
        try:
            document_id = self._generate_id(user_id, filename)

            document = Document(
                id=document_id,
                user_id=user_id,
                filename=filename,
                file_type=file_type,
                content=content,
                created_at=datetime.now().isoformat(),
                metadata={"uploaded_at": datetime.now().isoformat()},
            )

            chunks = self._chunker.chunk_text(content, document_id)
            document.chunk_count = len(chunks)

            if embedding_service.is_configured and chunks:
                texts = [c.content for c in chunks]
                try:
                    embeddings = await embedding_service.embed_with_retry(texts)
                    for chunk, emb in zip(chunks, embeddings):
                        chunk.embedding = emb.vector
                except Exception as e:
                    logger.warning(f"Failed to generate embeddings: {e}")

            self._documents[document_id] = document
            for chunk in chunks:
                self._chunks[chunk.id] = chunk

            if user_id not in self._user_documents:
                self._user_documents[user_id] = []
            self._user_documents[user_id].append(document_id)

            logger.info(f"Uploaded document {filename} with {len(chunks)} chunks")
            return document

        except Exception as e:
            logger.error(f"Failed to upload document: {e}")
            return None

    async def search(
        self,
        user_id: str,
        query: str,
        limit: int = 5,
    ) -> list[SearchResult]:
        """Search the knowledge base using semantic search."""
        if not embedding_service.is_configured:
            return self._keyword_search(user_id, query, limit)

        try:
            query_embedding = await embedding_service.embed_one(query)
            return self._semantic_search(user_id, query_embedding.vector, limit)
        except Exception as e:
            logger.warning(f"Semantic search failed, falling back to keyword: {e}")
            return self._keyword_search(user_id, query, limit)

    def _semantic_search(
        self, user_id: str, query_vector: list[float], limit: int
    ) -> list[SearchResult]:
        """Search using vector similarity."""
        results = []
        user_docs = self._user_documents.get(user_id, [])

        for doc_id in user_docs:
            doc = self._documents.get(doc_id)
            if not doc:
                continue

            for chunk in self._chunks.values():
                if chunk.document_id != doc_id or chunk.embedding is None:
                    continue

                score = self._cosine_similarity(query_vector, chunk.embedding)
                results.append(SearchResult(chunk=chunk, score=score, document=doc))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def _keyword_search(self, user_id: str, query: str, limit: int) -> list[SearchResult]:
        """Fallback keyword search."""
        results = []
        query_lower = query.lower()
        query_words = set(query_lower.split())
        user_docs = self._user_documents.get(user_id, [])

        for doc_id in user_docs:
            doc = self._documents.get(doc_id)
            if not doc:
                continue

            for chunk in self._chunks.values():
                if chunk.document_id != doc_id:
                    continue

                content_lower = chunk.content.lower()
                overlap = len(query_words & set(content_lower.split()))
                if overlap > 0:
                    score = overlap / len(query_words)
                    results.append(SearchResult(chunk=chunk, score=score, document=doc))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not a or not b or len(a) != len(b):
            return 0.0

        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot / (norm_a * norm_b)

    def get_document(self, document_id: str) -> Optional[Document]:
        return self._documents.get(document_id)

    def get_user_documents(self, user_id: str) -> list[Document]:
        doc_ids = self._user_documents.get(user_id, [])
        return [self._documents[did] for did in doc_ids if did in self._documents]

    def delete_document(self, document_id: str) -> bool:
        if document_id not in self._documents:
            return False

        doc = self._documents.pop(document_id)
        self._user_documents.get(doc.user_id, []).remove(document_id)

        chunks_to_delete = [cid for cid, c in self._chunks.items() if c.document_id == document_id]
        for cid in chunks_to_delete:
            del self._chunks[cid]

        return True

    def get_stats(self, user_id: str) -> dict:
        docs = self.get_user_documents(user_id)
        return {
            "total_documents": len(docs),
            "total_chunks": sum(d.chunk_count for d in docs),
            "file_types": list(set(d.file_type for d in docs)),
        }


knowledge_base = KnowledgeBase()
