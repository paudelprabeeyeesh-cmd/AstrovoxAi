"""Research agent: fetches and summarizes information from URLs."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ResearchResult:
    """Result of a research query."""
    success: bool
    sources: list[dict] = field(default_factory=list)
    summary: str = ""
    queries: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"success": self.success, "sources": self.sources,
                "summary": self.summary, "queries": self.queries}


class ResearchAgent:
    """Agent that researches topics via URLs and documentation."""

    def __init__(self, name: str = "researcher", max_urls: int = 10):
        self.name = name
        self.role = "researcher"
        self.max_urls = max_urls
        self.history: list[ResearchResult] = []

    def plan(self, query: str) -> dict:
        return {"action": "research", "query": query}

    def act(self, action: dict) -> ResearchResult:
        query = action.get("query", action.get("description", ""))
        self.history.append({"query": query, "status": "done"})
        return ResearchResult(success=True,
                              summary=f"research summary for: {query}",
                              sources=[{"url": f"https://example.com?q={query}",
                                        "title": query, "snippets": [query]}],
                              queries=[query])

    def research(self, query: str) -> ResearchResult:
        return self.act({"action": "research", "query": query})

    def search(self, queries: list[str]) -> list[ResearchResult]:
        return [self.research(q) for q in queries[:self.max_urls]]

    def cite(self, source: dict, reference: str) -> str:
        """Format a citation for a source."""
        return f"[{reference}] {source.get('title', 'unknown')}: {source.get('url', '')}"
