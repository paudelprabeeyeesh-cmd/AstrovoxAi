"""Unified Advanced Search Engine.

Combines BM25, dense retrieval, hybrid fusion, reranking,
web search, internal document search, image search, video search,
citation generation, and source verification into a single orchestrator.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.search_knowledge import (
    CrossEncoderReranker,
    SearchResult as SKSearchResult,
    SearchKnowledgePlatform,
)
from app.rag_engine import RAGEngine
from app.core.web_search import web_search
from app.search import SearchEngine as MemorySearchEngine

try:
    from ASTROVOX_AI.ai_core.search.image_search import ImageSearch
    from ASTROVOX_AI.ai_core.search.news_search import NewsSearch
    from ASTROVOX_AI.ai_core.search.academic_search import AcademicSearch
    from ASTROVOX_AI.ai_core.search.semantic_cache import SemanticCache
    HAS_ASTROVOX = True
except ImportError:
    HAS_ASTROVOX = False

logger = logging.getLogger(__name__)


@dataclass
class AdvancedSearchResult:
    title: str
    content: str
    url: str
    score: float
    source_type: str
    source_name: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    citation: Optional[str] = None
    verified: bool = False
    verification_score: float = 0.0
    highlights: List[str] = field(default_factory=list)
    chunk_id: Optional[str] = None
    document_id: Optional[str] = None


class UnifiedSearchEngine:
    def __init__(self):
        self.knowledge = SearchKnowledgePlatform()
        self.memory = MemorySearchEngine()
        self.rag = RAGEngine()
        self.web = web_search
        self.reranker = CrossEncoderReranker()
        self.citation_engine = self.knowledge.citation
        if HAS_ASTROVOX:
            self.images = ImageSearch()
            self.news = NewsSearch()
            self.academic = AcademicSearch()
            self.semantic_cache = SemanticCache()
        else:
            self.images = None
            self.news = None
            self.academic = None
            self.semantic_cache = None

    def search(
        self,
        query: str,
        user_id: str = "system",
        top_k: int = 10,
        alpha: float = 0.5,
        sources: Optional[List[str]] = None,
        include_web: bool = True,
        include_images: bool = False,
        include_videos: bool = False,
        include_news: bool = False,
        include_academic: bool = False,
        include_internal: bool = True,
        rerank: bool = True,
        generate_citations: bool = True,
        verify_sources: bool = True,
        query_embedding: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        start = time.time()
        sources = sources or ["hybrid", "web", "internal"]
        candidates: List[AdvancedSearchResult] = []
        source_types: List[str] = []

        if include_internal and any(s in sources for s in ["hybrid", "internal", "bm25", "dense", "semantic"]):
            internal = self._search_internal(query, user_id, top_k * 2, alpha, query_embedding)
            candidates.extend(internal)
            if internal:
                source_types.append("internal")

        if include_web and any(s in sources for s in ["hybrid", "web"]):
            web_results = self._search_web(query, top_k)
            candidates.extend(web_results)
            if web_results:
                source_types.append("web")

        if include_images and self.images:
            image_results = self._search_images(query, top_k)
            candidates.extend(image_results)
            if image_results:
                source_types.append("images")

        if include_videos:
            video_results = self._search_videos(query, top_k)
            candidates.extend(video_results)
            if video_results:
                source_types.append("videos")

        if include_news and self.news:
            news_results = self._search_news(query, top_k)
            candidates.extend(news_results)
            if news_results:
                source_types.append("news")

        if include_academic and self.academic:
            academic_results = self._search_academic(query, top_k)
            candidates.extend(academic_results)
            if academic_results:
                source_types.append("academic")

        if not candidates:
            candidates = [AdvancedSearchResult(
                title="No results",
                content="",
                url="",
                score=0.0,
                source_type="empty",
                source_name="system",
            )]

        if rerank and len(candidates) > 1:
            candidates = self._rerank_results(query, candidates, top_k)

        if verify_sources:
            candidates = self._verify_sources(candidates)

        if generate_citations:
            candidates = self._generate_citations(candidates)

        candidates.sort(key=lambda x: x.score, reverse=True)
        latency = (time.time() - start) * 1000

        return {
            "query": query,
            "results": [self._result_to_dict(r) for r in candidates[:top_k]],
            "sources": source_types,
            "latency_ms": round(latency, 2),
            "result_count": len(candidates[:top_k]),
        }

    def _search_internal(self, query: str, user_id: str, top_k: int, alpha: float, query_embedding: Optional[List[float]]) -> List[AdvancedSearchResult]:
        results = []
        try:
            hybrid = self.knowledge.hybrid_search(query, query_embedding, top_k=top_k, alpha=alpha)
            for r in hybrid:
                results.append(AdvancedSearchResult(
                    title=r.content[:100] if r.content else "Internal document",
                    content=r.content,
                    url="",
                    score=r.score,
                    source_type="internal",
                    source_name="hybrid_bm25_dense",
                    metadata=r.metadata or {},
                    highlights=[],
                    chunk_id=r.chunk_id,
                    document_id=r.document_id,
                ))
        except Exception as exc:
            logger.warning("Internal search failed: %s", exc)
        return results

    def _search_web(self, query: str, top_k: int) -> List[AdvancedSearchResult]:
        results = []
        try:
            web_results = self.web.search(query, max_results=top_k)
            for r in web_results:
                results.append(AdvancedSearchResult(
                    title=r.title,
                    content=r.snippet,
                    url=r.url,
                    score=float(r.score or 0.0),
                    source_type="web",
                    source_name=r.source or "web",
                ))
        except Exception as exc:
            logger.warning("Web search failed: %s", exc)
        return results

    def _search_images(self, query: str, top_k: int) -> List[AdvancedSearchResult]:
        results = []
        if not self.images:
            return results
        try:
            img_results = self.images.search(query, num_results=top_k)
            for r in img_results:
                results.append(AdvancedSearchResult(
                    title=r.get("title", ""),
                    content=r.get("context", r.get("snippet", "")),
                    url=r.get("link", ""),
                    score=0.5,
                    source_type="image",
                    source_name="image_search",
                    metadata={"thumbnail": r.get("thumbnail", "")},
                ))
        except Exception as exc:
            logger.warning("Image search failed: %s", exc)
        return results

    def _search_videos(self, query: str, top_k: int) -> List[AdvancedSearchResult]:
        results = []
        try:
            video_results = video_search(query, top_k)
            for r in video_results:
                results.append(AdvancedSearchResult(
                    title=r.get("title", ""),
                    content=r.get("description", r.get("snippet", "")),
                    url=r.get("url", ""),
                    score=float(r.get("score", 0.0)),
                    source_type="video",
                    source_name=r.get("source", "video_search"),
                    metadata={
                        "duration": r.get("duration"),
                        "thumbnail": r.get("thumbnail"),
                        "published_at": r.get("published_at"),
                    },
                ))
        except Exception as exc:
            logger.warning("Video search failed: %s", exc)
        return results

    def _search_news(self, query: str, top_k: int) -> List[AdvancedSearchResult]:
        results = []
        if not self.news:
            return results
        try:
            news_results = self.news.search(query, num_results=top_k)
            for r in news_results:
                results.append(AdvancedSearchResult(
                    title=r.get("title", ""),
                    content=r.get("description", ""),
                    url=r.get("url", ""),
                    score=0.6,
                    source_type="news",
                    source_name=r.get("source", "news"),
                    metadata={"published_at": r.get("published_at", "")},
                ))
        except Exception as exc:
            logger.warning("News search failed: %s", exc)
        return results

    def _search_academic(self, query: str, top_k: int) -> List[AdvancedSearchResult]:
        results = []
        if not self.academic:
            return results
        try:
            academic_results = self.academic.search(query, num_results=top_k)
            for r in academic_results:
                results.append(AdvancedSearchResult(
                    title=r.get("title", ""),
                    content=f"Citations: {r.get('citations', 'N/A')}",
                    url=r.get("url", ""),
                    score=0.7,
                    source_type="academic",
                    source_name=r.get("source", "academic"),
                    metadata={"year": r.get("year", ""), "citations": r.get("citations", 0)},
                ))
        except Exception as exc:
            logger.warning("Academic search failed: %s", exc)
        return results

    def _rerank_results(self, query: str, candidates: List[AdvancedSearchResult], top_k: int) -> List[AdvancedSearchResult]:
        try:
            sk_candidates = [
                SKSearchResult(
                    chunk_id=r.chunk_id or str(hash(r.url)),
                    document_id=r.document_id or r.url,
                    content=r.content,
                    score=r.score,
                    source=r.source_type,
                    metadata=r.metadata,
                    highlights=r.highlights,
                    citation=r.citation,
                )
                for r in candidates
            ]
            reranked = self.reranker.rerank(query, sk_candidates, top_k=top_k * 2)
            result_map = {r.content: r for r in candidates}
            final = []
            for rr in reranked:
                original = result_map.get(rr.content)
                if original:
                    original.score = rr.score
                    final.append(original)
            for r in candidates:
                if r not in final and len(final) < top_k * 2:
                    final.append(r)
            return final[:top_k * 2]
        except Exception as exc:
            logger.warning("Reranking failed: %s", exc)
            return candidates[:top_k * 2]

    def _verify_sources(self, candidates: List[AdvancedSearchResult]) -> List[AdvancedSearchResult]:
        for r in candidates:
            try:
                score, verified = verify_source(r.url, r.source_type)
                r.verification_score = score
                r.verified = verified
            except Exception:
                r.verification_score = 0.0
                r.verified = False
        return candidates

    def _generate_citations(self, candidates: List[AdvancedSearchResult]) -> List[AdvancedSearchResult]:
        for r in candidates:
            try:
                if r.source_type in ("web", "news", "academic", "video") and r.title:
                    citation = self.citation_engine.generate(
                        document_title=r.title,
                        authors=[],
                        year=str(r.metadata.get("year", "")) or str(__import__("datetime").datetime.now().year),
                        source=r.source_name,
                        url=r.url,
                        style="apa",
                    )
                    r.citation = citation.text
            except Exception:
                pass
        return candidates

    def _result_to_dict(self, r: AdvancedSearchResult) -> Dict[str, Any]:
        return {
            "title": r.title,
            "content": r.content,
            "url": r.url,
            "score": round(r.score, 4),
            "source_type": r.source_type,
            "source_name": r.source_name,
            "metadata": r.metadata,
            "citation": r.citation,
            "verified": r.verified,
            "verification_score": round(r.verification_score, 4),
            "highlights": r.highlights,
            "chunk_id": r.chunk_id,
            "document_id": r.document_id,
        }


def verify_source(url: str, source_type: str) -> tuple[float, bool]:
    if not url or not (url.startswith("http://") or url.startswith("https://")):
        return 0.0, False
    trusted_domains = {
        "wikipedia.org": 0.9,
        "github.com": 0.85,
        "arxiv.org": 0.9,
        "semanticscholar.org": 0.9,
        "google.com": 0.7,
        "gov": 0.95,
        "edu": 0.9,
        "medium.com": 0.6,
        "youtube.com": 0.5,
        "youtu.be": 0.5,
    }
    score = 0.3
    verified = False
    if url.startswith("https://"):
        score += 0.1
    for domain, trust in trusted_domains.items():
        if domain in url:
            score = max(score, trust)
            if trust >= 0.8:
                verified = True
    return min(score, 1.0), verified


def video_search(query: str, top_k: int = 10) -> List[Dict[str, Any]]:
    search_terms = [f"{query} video", f"{query} tutorial", f"watch {query}"]
    results = []
    seen = set()
    for term in search_terms:
        try:
            hits = web_search.search(term, max_results=top_k)
            for hit in hits:
                key = hit.url or hit.title
                if key and key not in seen:
                    seen.add(key)
                    results.append({
                        "title": hit.title,
                        "url": hit.url,
                        "snippet": hit.snippet,
                        "score": float(hit.score or 0.0),
                        "source": "video_web_search",
                        "description": hit.snippet,
                        "published_at": "",
                        "thumbnail": "",
                        "duration": None,
                    })
        except Exception:
            continue
    results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    return results[:top_k]
