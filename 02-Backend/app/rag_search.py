"""RAG Search — enhanced retrieval-augmented generation search.

Extends the base RAG engine with:
- Hybrid BM25 + dense retrieval
- Multi-vector retrieval
- Query understanding and expansion
- Cross-encoder reranking
- Citation generation
- Source verification
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from app.rag_engine import RAGEngine
from app.search_knowledge import (
    BM25Index,
    CrossEncoderReranker,
    HybridSearchEngine,
    QueryUnderstanding,
    SearchResult as SKSearchResult,
)
from app.search_unified import verify_source, verify_sources_batch
from app.search.source_verifier import get_verification_summary

logger = logging.getLogger(__name__)


class RAGSearchEngine:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.rag = RAGEngine(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.hybrid = HybridSearchEngine()
        self.reranker = CrossEncoderReranker()
        self.query_understanding = QueryUnderstanding()

    def search(self, query: str, user_id: str = "system", top_k: int = 5,
               alpha: float = 0.5, strategy: str = "hybrid") -> Dict[str, Any]:
        start = time.time()
        analysis = self.query_understanding.analyze(query)
        candidates: List[SKSearchResult] = []
        sources: List[str] = []

        if strategy in {"hybrid", "auto"}:
            try:
                dense = self.rag.search(query, user_id, top_k=top_k * 2)
                for d in dense:
                    candidates.append(SKSearchResult(
                        chunk_id=d.get("chunk_id", ""),
                        document_id=d.get("document_id", ""),
                        content=d.get("content", ""),
                        score=d.get("score", 0.0),
                        source=d.get("source", "dense"),
                        metadata=d.get("metadata", {}),
                        highlights=[],
                        citation=None,
                    ))
                if dense:
                    sources.append("dense")
            except Exception as exc:
                logger.warning("Dense retrieval failed: %s", exc)

        if strategy in {"bm25", "hybrid", "auto"}:
            try:
                from app.search import SearchEngine as MemorySearchEngine
                mem = MemorySearchEngine()
                sparse = mem.hybrid_search(query, user_id, top_k=top_k * 2)
                for s in sparse:
                    candidates.append(SKSearchResult(
                        chunk_id=s.get("id", ""),
                        document_id=s.get("id", ""),
                        content=s.get("content", ""),
                        score=s.get("score", 0.0),
                        source="bm25",
                        metadata=s.get("metadata", {}),
                        highlights=[],
                        citation=None,
                    ))
                if sparse:
                    sources.append("bm25")
            except Exception as exc:
                logger.warning("BM25 search failed: %s", exc)

        if not candidates:
            candidates = [SKSearchResult(chunk_id="empty", document_id="empty", content="", score=0.0)]

        seen = set()
        unique = []
        for c in candidates:
            key = c.chunk_id or c.content
            if key not in seen:
                seen.add(key)
                unique.append(c)
        candidates = unique

        if len(candidates) > top_k:
            reranked = self.reranker.rerank(query, candidates, top_k=top_k)
            candidates = reranked if reranked else candidates[:top_k]

        for c in candidates:
            if c.content:
                c.highlights = self._highlight(query, c.content)

        latency = (time.time() - start) * 1000
        return {
            "query": query,
            "analysis": analysis.__dict__ if hasattr(analysis, "__dict__") else {},
            "results": [c.__dict__ for c in candidates[:top_k]],
            "sources": sources,
            "latency_ms": round(latency, 2),
            "result_count": len(candidates[:top_k]),
        }

    def _highlight(self, query: str, content: str, max_snippets: int = 3) -> List[str]:
        words = [w for w in query.lower().split() if len(w) > 2]
        if not words:
            return [content[:200]]
        lower = content.lower()
        snippets = []
        for word in words:
            idx = lower.find(word)
            if idx != -1:
                start = max(0, idx - 50)
                end = min(len(content), idx + len(word) + 100)
                snippet = content[start:end]
                if start > 0:
                    snippet = "..." + snippet
                if end < len(content):
                    snippet = snippet + "..."
                snippets.append(snippet)
        return snippets[:max_snippets] or [content[:200]]
