import os
import re
import json
import hashlib
import requests
from datetime import datetime
from typing import Any

try:
    import openai
except ImportError:
    openai = None
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None
try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None

from ...documents import (
    create_document,
    delete_document_chunks,
    create_document_chunk,
    search_chunks,
    list_documents,
    get_document,
)
from ...config import settings


class _LazyOpenAIClient:
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            if openai is None:
                raise RuntimeError("openai is not installed")
            self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def __getattr__(self, name):
        return getattr(self._get_client(), name)


client = _LazyOpenAIClient()


class RAGEngine:
    def chunk_text(self, text, chunk_size=1000, overlap=200):
        if not text:
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

    def embed_chunks(self, chunks):
        if not chunks:
            return []
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=chunks,
        )
        return [item.embedding for item in response.data]

    def store_chunks(self, chunks, embeddings, user_id, source_type, filename=None):
        from app.repositories.database.client import get_db
        with get_db() as conn:
            row = conn.execute(
                "SELECT id FROM documents WHERE user_id = ? AND filename = ? ORDER BY created_at DESC LIMIT 1",
                (user_id, filename or source_type),
            ).fetchone()
            if row:
                doc_id = row["id"]
                delete_document_chunks(doc_id)
            else:
                doc = create_document(user_id, filename or source_type, source_type, sum(len(c) for c in chunks))
                doc_id = doc["id"]

        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            embedding_value = self._serialize_embedding(embedding)
            metadata = {"source_type": source_type, "chunk_index": idx}
            create_document_chunk(doc_id, chunk, embedding_value, metadata)

        return doc_id

    def _serialize_embedding(self, embedding):
        return list(embedding)

    def _deserialize_embedding(self, embedding_bytes):
        return list(embedding_bytes)

    def ingest_pdf(self, file_path, user_id):
        reader = PdfReader(file_path)
        text = "".join(page.extract_text() or "" for page in reader.pages)
        chunks = self.chunk_text(text)
        if not chunks:
            return []
        embeddings = self.embed_chunks(chunks)
        filename = os.path.basename(file_path)
        doc_id = self.store_chunks(chunks, embeddings, user_id, "pdf", filename)
        return [{"doc_id": doc_id, "chunks": len(chunks)}]

    def ingest_docx(self, file_path, user_id):
        doc = DocxDocument(file_path)
        text = "\n".join(para.text for para in doc.paragraphs)
        chunks = self.chunk_text(text)
        if not chunks:
            return []
        embeddings = self.embed_chunks(chunks)
        filename = os.path.basename(file_path)
        doc_id = self.store_chunks(chunks, embeddings, user_id, "docx", filename)
        return [{"doc_id": doc_id, "chunks": len(chunks)}]

    def ingest_txt(self, file_path, user_id):
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        chunks = self.chunk_text(text)
        if not chunks:
            return []
        embeddings = self.embed_chunks(chunks)
        filename = os.path.basename(file_path)
        doc_id = self.store_chunks(chunks, embeddings, user_id, "txt", filename)
        return [{"doc_id": doc_id, "chunks": len(chunks)}]

    def ingest_website(self, url, user_id):
        response = requests.get(url, timeout=30)
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

    def ingest_github_repo(self, repo_url, user_id):
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

    def search(self, query, user_id, top_k=5):
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
        reranked = self.rerank(query, combined[:top_k * 2], top_k=top_k)
        return reranked

    def _sparse_search(self, query, user_id, limit=10):
        from ...services.knowledge.knowledge import search_docs
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

    def rerank(self, query, chunks, top_k=5):
        if not chunks:
            return []
        query_embedding = self.embed_chunks([query])[0]
        scored = []
        for chunk in chunks:
            chunk_embedding = self.embed_chunks([chunk.get("content", "")])[0]
            score = self._cosine_similarity(query_embedding, chunk_embedding)
            scored.append({**chunk, "rerank_score": score})
        scored.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored[:top_k]

    def _cosine_similarity(self, a, b):
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)