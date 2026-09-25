"""RAG Engine — document ingestion, chunking, embedding, and retrieval.

Provides:
- Text chunking with overlap
- Embedding generation via OpenAI-compatible API
- Document and chunk storage
- PDF, DOCX, TXT, website, and GitHub repo ingestion
- Hybrid search (dense + sparse) with reranking
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
import uuid
from typing import Any, List, Optional

import requests

logger = logging.getLogger(__name__)

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


class _LazyOpenAIClient:
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            if openai is None:
                raise RuntimeError("openai is not installed")
            api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY is not set")
            self._client = openai.OpenAI(api_key=api_key)
        return self._client

    def __getattr__(self, name):
        return getattr(self._get_client(), name)


client = _LazyOpenAIClient()


class RAGEngine:
    """RAG engine for document ingestion and retrieval."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        embedding_model: str = "text-embedding-3-small",
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embedding_model = embedding_model

    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        if not text or not text.strip():
            return []
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk.strip())
            start = end - overlap
            if start >= len(text):
                break
        return chunks

    def embed_chunks(self, chunks: List[str]) -> List[List[float]]:
        if not chunks:
            return []
        if not HAS_OPENAI:
            raise RuntimeError("openai is not installed")
        response = client.embeddings.create(
            model=self.embedding_model,
            input=chunks,
        )
        return [item.embedding for item in response.data]

    def _serialize_embedding(self, embedding: List[float]) -> str:
        return json.dumps(embedding)

    def _deserialize_embedding(self, embedding_bytes: str) -> List[float]:
        return json.loads(embedding_bytes)

    def store_chunks(
        self,
        chunks: List[str],
        embeddings: List[List[float]],
        user_id: str,
        source_type: str,
        filename: Optional[str] = None,
    ) -> str:
        from app.documents import create_document, delete_document_chunks, create_document_chunk

        total_size = sum(len(c) for c in chunks)
        doc = create_document(user_id, filename or source_type, source_type, total_size)
        doc_id = doc["id"]

        delete_document_chunks(doc_id)

        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            embedding_value = self._serialize_embedding(embedding)
            metadata = {"source_type": source_type, "chunk_index": idx}
            create_document_chunk(doc_id, chunk, embedding_value, metadata)

        return doc_id

    def ingest_pdf(self, file_path: str, user_id: str) -> List[dict]:
        if not HAS_PYPDF:
            raise RuntimeError("pypdf is not installed")
        reader = PdfReader(file_path)
        text = "".join(page.extract_text() or "" for page in reader.pages)
        chunks = self.chunk_text(text)
        if not chunks:
            return []
        embeddings = self.embed_chunks(chunks)
        filename = os.path.basename(file_path)
        doc_id = self.store_chunks(chunks, embeddings, user_id, "pdf", filename)
        return [{"doc_id": doc_id, "chunks": len(chunks)}]

    def ingest_docx(self, file_path: str, user_id: str) -> List[dict]:
        if not HAS_DOCX:
            raise RuntimeError("python-docx is not installed")
        doc = DocxDocument(file_path)
        text = "\n".join(para.text for para in doc.paragraphs)
        chunks = self.chunk_text(text)
        if not chunks:
            return []
        embeddings = self.embed_chunks(chunks)
        filename = os.path.basename(file_path)
        doc_id = self.store_chunks(chunks, embeddings, user_id, "docx", filename)
        return [{"doc_id": doc_id, "chunks": len(chunks)}]

    def ingest_txt(self, file_path_or_bytes: Any, user_id: str, filename: str = "upload.txt") -> List[dict]:
        if isinstance(file_path_or_bytes, (bytes, bytearray)):
            text = file_path_or_bytes.decode("utf-8", errors="ignore")
        else:
            with open(file_path_or_bytes, "r", encoding="utf-8") as f:
                text = f.read()
        chunks = self.chunk_text(text)
        if not chunks:
            return []
        embeddings = self.embed_chunks(chunks)
        doc_id = self.store_chunks(chunks, embeddings, user_id, "txt", filename)
        return [{"doc_id": doc_id, "chunks": len(chunks)}]

    def ingest_website(self, url: str, user_id: str) -> List[dict]:
        if not HAS_BS4:
            raise RuntimeError("beautifulsoup4 is not installed")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for script in soup(["script", "style"]):
            script.decompose()
        text = soup.get_text(separator="\n")
        chunks = self.chunk_text(text)
        if not chunks:
            return []
        embeddings = self.embed_chunks(chunks)
        doc_id = self.store_chunks(chunks, embeddings, user_id, "website", url)
        return [{"doc_id": doc_id, "chunks": len(chunks)}]

    def ingest_github_repo(self, repo_url: str, user_id: str) -> List[dict]:
        api_url = repo_url.replace("github.com", "api.github.com/repos")
        if api_url.endswith("/"):
            api_url = api_url[:-1]
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        repo_data = response.json()
        default_branch = repo_data.get("default_branch", "main")
        contents_url = repo_data.get("contents_url", "").replace("{/path}", "/README.md")
        response = requests.get(contents_url, timeout=30)
        if response.status_code != 200:
            return []
        files = response.json()
        all_text = ""
        for file_info in files:
            if file_info.get("type") != "file":
                continue
            if not file_info.get("name", "").endswith((".md", ".py", ".txt", ".js", ".ts")):
                continue
            file_url = file_info.get("download_url")
            if not file_url:
                continue
            file_response = requests.get(file_url, timeout=30)
            if file_response.status_code == 200:
                all_text += f"\n\n# {file_info['name']}\n" + file_response.text
        chunks = self.chunk_text(all_text)
        if not chunks:
            return []
        embeddings = self.embed_chunks(chunks)
        doc_id = self.store_chunks(chunks, embeddings, user_id, "github", repo_url)
        return [{"doc_id": doc_id, "chunks": len(chunks)}]

    def search(self, query: str, user_id: str, top_k: int = 5) -> List[dict]:
        from app.documents import search_chunks

        query_embedding = self.embed_chunks([query])[0]
        embedding_bytes = self._serialize_embedding(query_embedding)
        dense_results = search_chunks(user_id, embedding_bytes, top_k * 2)
        dense = []
        for row in dense_results:
            dense.append({
                "chunk_id": row["id"],
                "document_id": row["document_id"],
                "content": row["content"],
                "filename": row["filename"],
                "metadata": row.get("metadata", {}),
                "score": float(row.get("score", 0.0)),
                "source": "dense",
            })

        sparse = self._sparse_search(query, user_id, top_k * 2)

        candidates = {c["chunk_id"]: c for c in dense}
        for s in sparse:
            cid = s.get("chunk_id")
            if cid in candidates:
                candidates[cid]["score"] = max(candidates[cid]["score"], s["score"] * 0.8)
                candidates[cid]["source"] = "hybrid"
            else:
                candidates[cid] = s
                candidates[cid]["source"] = "sparse"

        combined = list(candidates.values())
        combined.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        reranked = self.rerank(query, combined[: top_k * 2], top_k=top_k)
        return reranked

    def search_similar(self, query: str, user_id: str, top_k: int = 5) -> List[dict]:
        return self.search(query, user_id, top_k=top_k)

    def _sparse_search(self, query: str, user_id: str, limit: int = 10) -> List[dict]:
        from app.services.knowledge.knowledge import search_docs

        docs = search_docs(user_id, query, limit=limit)
        results = []
        for doc in docs:
            results.append({
                "chunk_id": doc.id,
                "document_id": doc.id,
                "content": doc.content,
                "filename": doc.title,
                "metadata": {},
                "score": 0.5,
                "source": "sparse",
            })
        return results

    def rerank(self, query: str, chunks: List[dict], top_k: int = 5) -> List[dict]:
        if not chunks:
            return []
        try:
            query_embedding = self.embed_chunks([query])[0]
        except Exception:
            query_embedding = [0.0] * 1536

        scored = []
        for chunk in chunks:
            content = chunk.get("content", "")
            try:
                chunk_embedding = self.embed_chunks([content])[0]
                score = self._cosine_similarity(query_embedding, chunk_embedding)
            except Exception:
                score = chunk.get("score", 0.0)
            scored.append({**chunk, "rerank_score": score})
        scored.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored[:top_k]

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
