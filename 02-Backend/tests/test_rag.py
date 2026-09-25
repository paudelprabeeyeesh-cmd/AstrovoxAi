"""Comprehensive RAG system tests."""

import time
import uuid
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.rag_engine import RAGEngine
from app.rag.hybrid_search import HybridSearchRAG, Document
from app.rag.reranker import Reranker
from app.documents import create_document, delete_document_chunks, create_document_chunk, search_chunks, list_documents, get_document


class TestRAGEngine:
    def setup_method(self):
        self.engine = RAGEngine()

    def test_chunk_text_empty(self):
        chunks = self.engine.chunk_text("")
        assert chunks == []

    def test_chunk_text_none(self):
        chunks = self.engine.chunk_text(None)
        assert chunks == []

    def test_chunk_text_short(self):
        text = "Short text"
        chunks = self.engine.chunk_text(text, chunk_size=1000, overlap=200)
        assert len(chunks) == 1
        assert chunks[0] == text.strip()

    def test_chunk_text_long(self):
        text = "A" * 2500
        chunks = self.engine.chunk_text(text, chunk_size=1000, overlap=200)
        assert len(chunks) > 1

    def test_chunk_text_overlap(self):
        text = "A" * 2500
        chunks = self.engine.chunk_text(text, chunk_size=1000, overlap=200)
        for i in range(len(chunks) - 1):
            chunk_end = chunks[i][-200:]
            next_start = chunks[i + 1][:200]
            assert chunk_end == next_start

    def test_chunk_text_strips_whitespace(self):
        text = "  Hello   World  "
        chunks = self.engine.chunk_text(text, chunk_size=1000, overlap=200)
        assert chunks[0] == "Hello   World"

    def test_serialize_embedding(self):
        emb = [0.1, 0.2, 0.3]
        serialized = self.engine._serialize_embedding(emb)
        assert isinstance(serialized, str)

    def test_serialize_embedding_empty(self):
        serialized = self.engine._serialize_embedding([])
        assert isinstance(serialized, str)

    @patch("app.rag_engine.client")
    def test_embed_chunks_empty(self, mock_client):
        embeddings = self.engine.embed_chunks([])
        assert embeddings == []

    @patch("app.rag_engine.client")
    def test_embed_chunks_success(self, mock_client):
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536) for _ in range(2)]
        mock_client.embeddings.create.return_value = mock_response
        embeddings = self.engine.embed_chunks(["text1", "text2"])
        assert len(embeddings) == 2
        assert all(len(e) == 1536 for e in embeddings)

    def test_embed_chunks_openai_not_installed(self):
        with patch("app.rag_engine.openai", None):
            engine = RAGEngine()
            with pytest.raises(RuntimeError):
                engine.embed_chunks(["text"])

    def test_store_chunks_creates_document(self):
        with patch("app.rag_engine.get_db") as mock_get_db, \
             patch("app.rag_engine.create_document", return_value={"id": 1}) as mock_create_doc, \
             patch("app.rag_engine.create_document_chunk") as mock_create_chunk, \
             patch("app.rag_engine.delete_document_chunks"):
            mock_conn = MagicMock()
            mock_conn.execute.return_value.fetchone.return_value = None
            mock_get_db.return_value.__enter__.return_value = mock_conn
            chunks = ["chunk1", "chunk2"]
            embeddings = [[0.1] * 1536, [0.2] * 1536]
            doc_id = self.engine.store_chunks(chunks, embeddings, "user-1", "text", filename="test.txt")
            assert doc_id == 1

    def test_store_chunks_reuses_existing_document(self):
        with patch("app.rag_engine.get_db") as mock_get_db, \
             patch("app.rag_engine.create_document_chunk") as mock_create_chunk, \
             patch("app.rag_engine.delete_document_chunks"):
            mock_conn = MagicMock()
            mock_conn.execute.return_value.fetchone.return_value = {"id": 5}
            mock_get_db.return_value.__enter__.return_value = mock_conn
            chunks = ["chunk1"]
            embeddings = [[0.1] * 1536]
            doc_id = self.engine.store_chunks(chunks, embeddings, "user-1", "text", filename="test.txt")
            assert doc_id == 5

    @patch("app.rag_engine.client")
    def test_ingest_txt_file(self, mock_client):
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_client.embeddings.create.return_value = mock_response
        result = self.engine.ingest_txt(b"Hello world", "user-1", filename="test.txt")
        assert isinstance(result, list)

    def test_ingest_txt_creates_chunks(self):
        with patch("app.rag_engine.client") as mock_client, \
             patch("app.rag_engine.create_document", return_value={"id": 1}), \
             patch("app.rag_engine.create_document_chunk"):
            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
            mock_client.embeddings.create.return_value = mock_response
            result = self.engine.ingest_txt(b"x" * 2000, "user-1", filename="test.txt")
            assert len(result) > 0

    @patch("app.rag_engine.client")
    def test_search_similar(self, mock_client):
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_client.embeddings.create.return_value = mock_response
        with patch("app.rag_engine.search_chunks", return_value=[]):
            results = self.engine.search_similar("AI", "user-1", top_k=5)
            assert isinstance(results, list)

    @patch("app.rag_engine.client")
    def test_search_similar_returns_chunks(self, mock_client):
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_client.embeddings.create.return_value = mock_response
        with patch("app.rag_engine.search_chunks", return_value=[{"chunk": "AI is cool", "score": 0.9}]):
            results = self.engine.search_similar("AI", "user-1", top_k=5)
            assert len(results) > 0


class TestHybridSearchRAG:
    def setup_method(self):
        self.rag = HybridSearchRAG()

    def test_index_document(self):
        doc = Document(doc_id="doc1", text="Python is great", embedding=[0.1, 0.2, 0.3])
        self.rag.index(doc)
        assert "doc1" in self.rag._documents

    def test_index_document_without_embedding(self):
        doc = Document(doc_id="doc1", text="Python is great")
        self.rag.index(doc)
        assert "doc1" in self.rag._documents
        assert "doc1" not in self.rag._vector_index

    def test_search_with_bm25(self):
        doc1 = Document(doc_id="doc1", text="Python programming")
        doc2 = Document(doc_id="doc2", text="JavaScript coding")
        self.rag.index(doc1)
        self.rag.index(doc2)
        results = self.rag.search("Python", top_k=2)
        assert len(results) <= 2

    def test_search_empty_index(self):
        results = self.rag.search("Python", top_k=5)
        assert results == []

    def test_search_with_query_embedding(self):
        doc = Document(doc_id="doc1", text="AI machine learning", embedding=[0.1, 0.2, 0.3])
        self.rag.index(doc)
        results = self.rag.search("AI", query_embedding=[0.1, 0.2, 0.3], top_k=5)
        assert len(results) <= 5

    def test_bm25_search(self):
        doc = Document(doc_id="doc1", text="Python Python Python")
        self.rag.index(doc)
        results = self.rag._bm25_search("Python", top_k=5)
        assert len(results) >= 1
        assert results[0][0] == "doc1"

    def test_vector_search(self):
        doc = Document(doc_id="doc1", text="test", embedding=[1.0, 0.0, 0.0])
        self.rag.index(doc)
        results = self.rag._vector_search([1.0, 0.0, 0.0], top_k=5)
        assert len(results) >= 1
        assert results[0][0] == "doc1"

    def test_vector_search_no_embeddings(self):
        results = self.rag._vector_search([1.0, 0.0, 0.0], top_k=5)
        assert results == []

    def test_vector_search_zero_norm(self):
        doc = Document(doc_id="doc1", text="test", embedding=[0.0, 0.0, 0.0])
        self.rag.index(doc)
        results = self.rag._vector_search([1.0, 0.0, 0.0], top_k=5)
        assert results[0][1] == 0.0

    def test_rerank(self):
        doc1 = Document(doc_id="doc1", text="Python programming tutorial")
        doc2 = Document(doc_id="doc2", text="JavaScript basics")
        self.rag.index(doc1)
        self.rag.index(doc2)
        candidates = ["doc1", "doc2"]
        results = self.rag.rerank("Python tutorial", candidates, top_k=2)
        assert len(results) <= 2
        assert results[0][0] == "doc1"

    def test_rerank_empty_candidates(self):
        results = self.rag.rerank("query", [], top_k=5)
        assert results == []

    def test_rerank_missing_document(self):
        self.rag.index(Document(doc_id="doc1", text="Python"))
        results = self.rag.rerank("query", ["doc1", "nonexistent"], top_k=5)
        assert len(results) == 1


class TestReranker:
    def setup_method(self):
        self.reranker = Reranker()

    def test_rerank_by_relevance(self):
        docs = [
            {"id": "1", "text": "Python is great", "score": 0.5},
            {"id": "2", "text": "Python programming tutorial", "score": 0.6},
        ]
        results = self.reranker.rerank("Python tutorial", docs)
        assert len(results) <= len(docs)

    def test_rerank_empty_list(self):
        results = self.reranker.rerank("query", [])
        assert results == []
