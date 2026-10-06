"""Keyword search using TF-IDF / BM25-style scoring."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class KeywordHit:
    """A keyword search hit."""
    key: str
    score: float
    text: str

    def to_dict(self) -> dict:
        return {"key": self.key, "score": self.score, "text": self.text}


class KeywordSearch:
    """TF-IDF/BM25-style keyword search."""

    def __init__(self, k1: float = 1.5, b: float = 0.75, delta: float = 1.2):
        self.k1 = k1
        self.b = b
        self.delta = delta
        self._docs: list[dict] = []
        self._index: dict[str, dict[str, int]] = {}
        self._doc_lens: dict[str, int] = {}

    def _term_freq(self, term: str, text: str) -> float:
        return text.lower().count(term) / max(len(text.split()), 1)

    def _inverse_doc_freq(self, term: str) -> float:
        docs_with = sum(1 for t in self._index.values() if term in t)
        return math.log((len(self._docs) + 1) / (docs_with + 1)) + 1.0

    def add(self, key: str, text: str, metadata: dict | None = None) -> None:
        """Index a document."""
        text = str(text).lower()
        self._docs.append({"key": key, "text": text, "metadata": metadata or {}})
        self._doc_lens[key] = len(text.split())
        terms = {}
        for t in text.split():
            terms[t] = terms.get(t, 0) + 1
        self._index[key] = terms

    def search(self, query: str, top: int = 10) -> list[KeywordHit]:
        """Search using BM25-style scoring."""
        q_terms = query.lower().split()
        scores: dict[str, float] = {}
        avg_dl = sum(self._doc_lens.values()) / max(len(self._docs), 1)
        for term in q_terms:
            idf = self._inverse_doc_freq(term)
            for key, terms in self._index.items():
                if term not in terms:
                    continue
                tf = self._term_freq(term, self._docs[key]["text"])
                dl = self._doc_lens[key]
                bm25 = idf * tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * dl / max(avg_dl, 1)))
                scores[key] = scores.get(key, 0.0) + bm25
        hits = []
        for key, score in scores.items():
            hits.append(KeywordHit(key=key, score=score, text=self._docs[key]["text"]))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:top]

    def count(self) -> int:
        return len(self._docs)

    def clear(self) -> None:
        self._docs.clear()
        self._index.clear()
        self._doc_lens.clear()
