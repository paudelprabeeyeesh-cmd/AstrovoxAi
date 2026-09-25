"""RAG: BM25 search."""

from __future__ import annotations

import logging
import re
from collections import Counter
from typing import List, Tuple

logger = logging.getLogger(__name__)


class BM25Search:
    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self._documents: List[str] = []
        self._doc_tokens: List[List[str]] = []
        self._avgdl: float = 0.0
        self._idf: dict[str, float] = {}

    def index(self, documents: List[str]) -> None:
        self._documents = documents
        self._doc_tokens = [self._tokenize(doc) for doc in documents]
        doc_lengths = [len(tokens) for tokens in self._doc_tokens]
        self._avgdl = sum(doc_lengths) / max(len(doc_lengths), 1)
        df = Counter()
        for tokens in self._doc_tokens:
            for token in set(tokens):
                df[token] += 1
        n = len(self._doc_tokens)
        self._idf = {token: max(0.0, (n - freq + 0.5) / (freq + 0.5) + 1.0) for token, freq in df.items()}

    def search(self, query: str, top_k: int = 5) -> List[Tuple[int, float]]:
        query_tokens = self._tokenize(query)
        scores = []
        for idx, tokens in enumerate(self._doc_tokens):
            score = self._score(query_tokens, tokens)
            scores.append((idx, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"\w+", text.lower())

    def _score(self, query_tokens: List[str], doc_tokens: List[str]) -> float:
        doc_len = len(doc_tokens)
        tf = Counter(doc_tokens)
        score = 0.0
        for token in query_tokens:
            idf = self._idf.get(token, 0.0)
            freq = tf.get(token, 0)
            numerator = freq * (self.k1 + 1)
            denominator = freq + self.k1 * (1 - self.b + self.b * doc_len / max(self._avgdl, 1))
            score += idf * numerator / max(denominator, 1e-9)
        return score
