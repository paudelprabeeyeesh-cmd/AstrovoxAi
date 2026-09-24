"""
Document Ingestion Pipeline for RAG.

Supports ingestion from:
- PDF files
- DOCX files
- TXT files
- Websites (URL)
- GitHub repositories

Pipeline stages:
1. Text extraction
2. Chunking
3. Embedding generation
4. Storage in database
"""

from __future__ import annotations

import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

import numpy as np

from ..documents import (
    create_document,
    delete_document_chunks,
    create_document_chunk,
    search_chunks,
    get_document,
    list_documents,
    delete_document,
)
from retrieval.chunker import (
    fixed_size_chunk,
    sentence_aware_chunk,
    paragraph_aware_chunk,
    hierarchical_chunk,
    Chunker,
)
from app.parsers.document_parsers import DocumentParsers

logger = logging.getLogger(__name__)


@dataclass
class DocumentIngestionResult:
    document_id: str
    filename: str
    source_type: str
    chunks_created: int
    total_characters: int
    created_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class TextExtractor:
    """Extract text from various file formats."""

    @staticmethod
    def extract_txt(file_path: str) -> str:
        return DocumentParsers.parse_txt(file_path)

    @staticmethod
    def extract_pdf(file_path: str) -> str:
        return DocumentParsers.parse_pdf(file_path)

    @staticmethod
    def extract_docx(file_path: str) -> str:
        return DocumentParsers.parse_docx(file_path)

    @staticmethod
    def extract_markdown(file_path: str) -> str:
        return DocumentParsers.parse_markdown(file_path)

    @staticmethod
    def extract_html(file_path: str) -> str:
        return DocumentParsers.parse_html(file_path)

    @staticmethod
    def extract_csv(file_path: str) -> str:
        return DocumentParsers.parse_csv(file_path)

    @staticmethod
    def extract_website(url: str) -> str:
        try:
            import requests
            from bs4 import BeautifulSoup
        except ImportError:
            raise RuntimeError("requests and beautifulsoup4 are required for website ingestion.")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for script in soup(["script", "style"]):
            script.decompose()
        text = soup.get_text(separator="\n")
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        return "\n".join(chunk for chunk in chunks if chunk)

    @staticmethod
    def extract_github_repo(repo_url: str) -> str:
        try:
            import requests
        except ImportError:
            raise RuntimeError("requests is required for GitHub ingestion.")
        api_url = repo_url.replace("github.com", "api.github.com/repos")
        if api_url.endswith("/"):
            api_url = api_url[:-1]
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        repo_data = response.json()
        default_branch = repo_data.get("default_branch", "main")
        contents_url = repo_data.get("contents_url", "").replace("{/path}", "/")
        response = requests.get(contents_url, timeout=30)
        if response.status_code != 200:
            return ""
        files = response.json()
        all_text = ""
        for file_info in files:
            if file_info.get("type") != "file":
                continue
            if not file_info.get("name", "").endswith((".md", ".py", ".txt", ".js", ".ts", ".json", ".yaml", ".yml")):
                continue
            file_url = file_info.get("download_url")
            if not file_url:
                continue
            file_response = requests.get(file_url, timeout=30)
            if file_response.status_code == 200:
                all_text += f"\n\n# {file_info['name']}\n" + file_response.text
        return all_text


class ChunkingPipeline:
    """Configurable chunking pipeline with multiple strategies."""

    def __init__(
        self,
        strategy: str = "sentence",
        chunk_size: int = 500,
        overlap: int = 50,
        max_chunk_size: int = 1000,
        similarity_threshold: float = 0.5,
    ):
        self.strategy = strategy
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.max_chunk_size = max_chunk_size
        self.similarity_threshold = similarity_threshold
        self._chunker = Chunker(
            strategy=strategy,
            chunk_size=chunk_size,
            overlap=overlap,
            max_chunk_size=max_chunk_size,
            similarity_threshold=similarity_threshold,
        )

    def chunk(self, text: str) -> List[str]:
        if not text or not text.strip():
            return []
        chunks = self._chunker.chunk(text)
        return [c for c in chunks if c and c.strip()]


class EmbeddingPipeline:
    """Generate embeddings for text chunks with batching and retry."""

    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size

    async def embed_chunks(self, chunks: List[str]) -> List[List[float]]:
        if not chunks:
            return []
        from ..embeddings import embedding_service
        results: List[List[float]] = []
        for i in range(0, len(chunks), self.batch_size):
            batch = chunks[i : i + self.batch_size]
            try:
                vectors = await embedding_service.embed_with_retry(texts=batch)
                results.extend([v.vector for v in vectors])
            except Exception as exc:
                logger.error("Embedding batch failed: %s", exc)
                for _ in batch:
                    results.append([])
        return results


class StoragePipeline:
    """Store document chunks and embeddings in the database."""

    def store(
        self,
        user_id: str,
        filename: str,
        source_type: str,
        chunks: List[str],
        embeddings: List[List[float]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DocumentIngestionResult:
        if len(chunks) != len(embeddings):
            raise ValueError("Chunks and embeddings length mismatch")
        total_characters = sum(len(c) for c in chunks)
        doc = create_document(
            user_id=user_id,
            filename=filename,
            content_type=source_type,
            size=total_characters,
        )
        doc_id = doc["id"]
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            if not embedding:
                continue
            chunk_metadata = {
                "source_type": source_type,
                "chunk_index": idx,
                "total_chunks": len(chunks),
            }
            if metadata:
                chunk_metadata.update(metadata)
            create_document_chunk(doc_id, chunk, embedding, chunk_metadata)
        return DocumentIngestionResult(
            document_id=doc_id,
            filename=filename,
            source_type=source_type,
            chunks_created=len(chunks),
            total_characters=total_characters,
            created_at=datetime.now(timezone.utc).isoformat(),
            metadata=metadata or {},
        )



class RAGPipeline:
    """
    Unified document ingestion pipeline.
    
    Usage:
        pipeline = RAGPipeline(user_id="user123")
        result = await pipeline.ingest_file("/path/to/doc.pdf", "mydoc.pdf", "pdf")
        result = await pipeline.ingest_website("https://example.com", "example")
        result = await pipeline.ingest_github_repo("https://github.com/owner/repo", "repo")
    """

    def __init__(
        self,
        user_id: str,
        chunking_strategy: str = "sentence",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        max_chunk_size: int = 1000,
        embedding_batch_size: int = 100,
    ):
        self.user_id = user_id
        self.text_extractor = TextExtractor()
        self.chunking_pipeline = ChunkingPipeline(
            strategy=chunking_strategy,
            chunk_size=chunk_size,
            overlap=chunk_overlap,
            max_chunk_size=max_chunk_size,
        )
        self.embedding_pipeline = EmbeddingPipeline(batch_size=embedding_batch_size)
        self.storage_pipeline = StoragePipeline()

    async def ingest_text(
        self,
        text: str,
        filename: str = "text",
        source_type: str = "txt",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DocumentIngestionResult:
        """Ingest raw text."""
        chunks = self.chunking_pipeline.chunk(text)
        if not chunks:
            raise ValueError("No chunks generated from text")
        embeddings = await self.embedding_pipeline.embed_chunks(chunks)
        return self.storage_pipeline.store(
            user_id=self.user_id,
            filename=filename,
            source_type=source_type,
            chunks=chunks,
            embeddings=embeddings,
            metadata=metadata,
        )

    async def ingest_file(
        self,
        file_path: str,
        filename: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DocumentIngestionResult:
        """Ingest a file from disk."""
        if filename is None:
            filename = os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()
        source_type = ext.lstrip(".") or "txt"
        extractors = {
            ".pdf": self.text_extractor.extract_pdf,
            ".docx": self.text_extractor.extract_docx,
            ".txt": self.text_extractor.extract_txt,
            ".md": self.text_extractor.extract_markdown,
            ".html": self.text_extractor.extract_html,
            ".htm": self.text_extractor.extract_html,
            ".csv": self.text_extractor.extract_csv,
        }
        extractor = extractors.get(ext, self.text_extractor.extract_txt)
        text = extractor(file_path)
        if not text or not text.strip():
            raise ValueError(f"No text extracted from {filename}")
        return await self.ingest_text(text, filename=filename, source_type=source_type, metadata=metadata)

    async def ingest_website(
        self,
        url: str,
        filename: str = "website",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DocumentIngestionResult:
        """Ingest content from a website."""
        if metadata is None:
            metadata = {}
        metadata["source_url"] = url
        text = self.text_extractor.extract_website(url)
        if not text or not text.strip():
            raise ValueError(f"No text extracted from {url}")
        return await self.ingest_text(text, filename=filename, source_type="website", metadata=metadata)

    async def ingest_github_repo(
        self,
        repo_url: str,
        filename: str = "github_repo",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DocumentIngestionResult:
        """Ingest a GitHub repository."""
        if metadata is None:
            metadata = {}
        metadata["repo_url"] = repo_url
        text = self.text_extractor.extract_github_repo(repo_url)
        if not text or not text.strip():
            raise ValueError(f"No text extracted from {repo_url}")
        return await self.ingest_text(text, filename=filename, source_type="github", metadata=metadata)
