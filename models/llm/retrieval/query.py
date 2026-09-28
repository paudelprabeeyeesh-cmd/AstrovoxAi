"""Query rewriting and expansion for improved retrieval."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

SEPARATORS = [".", "?", "!", "\n"]


@dataclass
class ExpandedQuery:
    original: str
    queries: list[str]
    decomposition: list[str] | None = None


class QueryExpander:
    def __init__(
        self,
        max_expansions: int = 3,
        use_decomposition: bool = True,
        use_multi_query: bool = True,
        synonym_fn=None,
    ):
        self.max_expansions = max_expansions
        self.use_decomposition = use_decomposition
        self.use_multi_query = use_multi_query
        self.synonym_fn = synonym_fn

    def expand(self, query: str) -> list[str]:
        queries = [query]
        if self.use_decomposition:
            decomposed = self._decompose(query)
            queries.extend(decomposed)
        if self.use_multi_query:
            multi = self._generate_multi_queries(query)
            queries.extend(multi)
        seen: set[str] = set()
        unique = []
        for q in queries:
            q_lower = q.lower().strip()
            if q_lower not in seen:
                seen.add(q_lower)
                unique.append(q.strip())
        return unique[: self.max_expansions + 1]

    def _decompose(self, query: str) -> list[str]:
        sub_queries = []
        parts = query.split(" and ")
        if len(parts) > 1:
            sub_queries = [p.strip() for p in parts if p.strip()]
        return sub_queries[: self.max_expansions]

    def _generate_multi_queries(self, query: str) -> list[str]:
        queries = [query]
        if self.synonym_fn is not None:
            for sep in SEPARATORS:
                if sep in query:
                    segments = query.split(sep)
                    for seg in segments:
                        seg = seg.strip()
                        if not seg:
                            continue
                        synonyms = self.synonym_fn(seg)
                        for syn in synonyms[:2]:
                            q = query.replace(seg, syn)
                            if q not in queries:
                                queries.append(q)
        if len(queries) <= 1:
            paraphrases = [
                query,
                query.replace("what is", "explain"),
                query.replace("how to", "ways to"),
            ]
            queries.extend(paraphrases[1:])
        return queries[: self.max_expansions]

    def decompose(self, query: str) -> list[str]:
        return self._decompose(query)

    def multi_query_generation(self, query: str, num_queries: int = 3) -> list[str]:
        expansions = []
        expansions.append(f"Explain {query}")
        expansions.append(f"Details about {query}")
        expansions.append(f"Key aspects of {query}")
        return expansions[:num_queries]
