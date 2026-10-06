"""Memory ranking: relevance scoring and ranking of recalled items."""

from __future__ import annotations

import math
import re
import time


def tfidf_score(term: str, text: str, corpus: list[str]) -> float:
    """Compute TF-IDF score for a term against a document in a corpus."""
    tf = text.lower().count(term.lower()) / max(len(text.split()), 1)
    df = sum(1 for d in corpus if term.lower() in d.lower())
    idf = math.log(len(corpus) / (1 + df)) + 1.0
    return tf * idf


def hybrid_rank(query: str, items: list[dict], corpus: list[str],
                weights: tuple[float, float, float] = (0.5, 0.4, 0.1),
                use_key: bool = True) -> list[dict]:
    """Rank items by keyword, semantic, and metadata scores."""
    scored = []
    for item in items:
        text = " ".join(str(v) for v in item.values())
        kw = sum(tfidf_score(t, text, corpus) for t in query.lower().split() if len(t) > 2)
        key_score = sum(tfidf_score(t, str(item.get("key", "")), corpus)
                        for t in query.lower().split()) if use_key else 0.0
        meta = item.get("importance", 1.0) + (item.get("recency", 0.0) * 0.001)
        total = kw * weights[0] + key_score * weights[1] + meta * weights[2]
        scored.append((total, item))
    scored.sort(reverse=True)
    return [item for _, item in scored]


def recency_boost(items: list[dict], now: float | None = None) -> list[dict]:
    """Boost items by recency."""
    now = now or time.time()
    scored = []
    for item in items:
        created = item.get("created", now)
        recency = 1.0 / (1.0 + (now - created))
        item = item.copy()
        item["recency"] = recency
        scored.append((recency, item))
    scored.sort(reverse=True)
    return [item for _, item in scored]


def deduplicate(items: list[dict], similarity_threshold: float = 0.9) -> list[dict]:
    """Deduplicate near-identical items."""
    kept = []
    for item in items:
        text = str(item).lower()
        if any(len(text) > 0 and all(c in str(k).lower() for c in text[:20]) for k in kept):
            continue
        kept.append(item)
    return kept


class Ranker:
    """Ranked retrieval with keyword + metadata scoring."""

    def __init__(self, corpus: list[str] | None = None):
        self.corpus = corpus or []

    def rank(self, query: str, items: list[dict], top: int = 20,
             weights: tuple[float, float, float] = (0.5, 0.4, 0.1)) -> list[dict]:
        scored = hybrid_rank(query, items, self.corpus, weights=weights)
        scored = recency_boost(scored)
        scored = deduplicate(scored)
        return scored[:top]

    def add_corpus(self, text: str) -> None:
        self.corpus.append(text)

    def score(self, query: str, item: dict) -> float:
        results = self.rank(query, [item], top=1)
        return results[0].get("recency", 0.0) if results else 0.0
