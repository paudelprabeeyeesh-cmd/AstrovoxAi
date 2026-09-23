"""
Web search integration for real-time information retrieval.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import List, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    score: float
    source: str = "web"


class WebSearchEngine:
    """Web search engine integration."""

    def __init__(self, api_key: Optional[str] = None, search_engine_id: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY", "")
        self.search_engine_id = search_engine_id or os.getenv("GOOGLE_CSE_ID", "")
        self.client = httpx.Client(timeout=15.0)
        self.cache: Dict[str, List[SearchResult]] = {}
        self.cache_ttl = 600

    def search(self, query: str, max_results: int = 10, use_cache: bool = True) -> List[SearchResult]:
        """Search the web for query."""
        cache_key = f"{query}:{max_results}"
        if use_cache and cache_key in self.cache:
            return self.cache[cache_key]
        results = self._search_google(query, max_results)
        self.cache[cache_key] = results
        return results

    def _search_google(self, query: str, max_results: int) -> List[SearchResult]:
        if not self.api_key or not self.search_engine_id:
            return [SearchResult(title="Search unavailable", url="", snippet="Configure GOOGLE_API_KEY and GOOGLE_CSE_ID", score=0.0, source="error")]
        try:
            url = f"https://www.googleapis.com/customsearch/v1"
            params = {"key": self.api_key, "cx": self.search_engine_id, "q": query, "num": min(max_results, 10)}
            response = self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            results = []
            for item in data.get("items", []):
                results.append(SearchResult(title=item.get("title", ""), url=item.get("link", ""), snippet=item.get("snippet", ""), score=item.get("score", 0.0), source="google"))
            return results
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return [SearchResult(title="Search error", url="", snippet=str(e), score=0.0, source="error")]

    def search_and_format(self, query: str, max_results: int = 5) -> str:
        """Search and format results as text."""
        results = self.search(query, max_results)
        if not results:
            return "No search results found."
        formatted = []
        for i, result in enumerate(results[:max_results], 1):
            formatted.append(f"[{i}] {result.title}\n{result.url}\n{result.snippet}\n")
        return "\n".join(formatted)


import os

web_search = WebSearchEngine()
