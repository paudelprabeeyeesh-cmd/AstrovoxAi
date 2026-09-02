"""Universal search engine with hybrid ranking and incremental indexing."""

from __future__ import annotations

import math
import re
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from . import make_id, now
from .memory import VectorIndex, _cosine


class SearchModality(str, Enum):
    DOCUMENT = "document"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    CONVERSATION = "conversation"
    MEMORY = "memory"
    CODE = "code"
    PLUGIN = "plugin"
    LOG = "log"


_TOKEN_PATTERN = re.compile(r"[\w]+", re.UNICODE)


def _tokenize(text: str) -> List[str]:
    return [t.lower() for t in _TOKEN_PATTERN.findall(text or "")]


@dataclass
class SearchDocument:
    id: str
    modality: SearchModality
    title: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    created_at: float = field(default_factory=now)
    updated_at: float = field(default_factory=now)
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "modality": self.modality.value,
            "title": self.title,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
        }


@dataclass
class SearchHit:
    doc: SearchDocument
    score: float
    lexical_score: float
    semantic_score: float
    personalization: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.doc.id,
            "modality": self.doc.modality.value,
            "title": self.doc.title,
            "score": round(self.score, 4),
            "lexical_score": round(self.lexical_score, 4),
            "semantic_score": round(self.semantic_score, 4),
            "personalization": round(self.personalization, 4),
            "metadata": self.doc.metadata,
        }


class LexicalIndex:
    """Inverted index for keyword search."""

    def __init__(self) -> None:
        self._postings: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._docs: Dict[str, SearchDocument] = {}
        self._doc_lengths: Dict[str, int] = {}
        self._avg_doc_length: float = 1.0

    def add(self, doc: SearchDocument) -> None:
        # Remove old postings if updating
        if doc.id in self._docs:
            self.remove(doc.id)
        tokens = _tokenize(doc.content)
        if not tokens:
            return
        self._docs[doc.id] = doc
        self._doc_lengths[doc.id] = len(tokens)
        for token in tokens:
            self._postings[token][doc.id] += 1
        self._avg_doc_length = sum(self._doc_lengths.values()) / max(len(self._doc_lengths), 1)

    def remove(self, doc_id: str) -> None:
        if doc_id not in self._docs:
            return
        for token, postings in list(self._postings.items()):
            postings.pop(doc_id, None)
            if not postings:
                del self._postings[token]
        self._doc_lengths.pop(doc_id, None)
        self._docs.pop(doc_id, None)

    def search(self, query: str, *, k: int = 10) -> List[Tuple[str, float]]:
        tokens = _tokenize(query)
        if not tokens:
            return []
        scores: Dict[str, float] = defaultdict(float)
        N = max(len(self._docs), 1)
        for token in tokens:
            posting = self._postings.get(token)
            if not posting:
                continue
            df = len(posting)
            idf = math.log((N - df + 0.5) / (df + 0.5) + 1)
            for doc_id, tf in posting.items():
                length_norm = 1 + math.log(1 + self._avg_doc_length / max(self._doc_lengths.get(doc_id, 1), 1))
                scores[doc_id] += idf * (tf / (tf + 0.5 + 1.5 * length_norm))
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        return ranked[:k]


class UniversalSearch:
    """Hybrid search: lexical + semantic + personalization."""

    def __init__(self) -> None:
        self.lexical = LexicalIndex()
        self.vector = VectorIndex()
        self._docs: Dict[str, SearchDocument] = {}
        self._user_history: Dict[str, List[str]] = defaultdict(list)

    def index(self, doc: SearchDocument) -> SearchDocument:
        doc.id = doc.id or make_id("doc")
        doc.updated_at = now()
        if doc.id in self._docs:
            doc.version = self._docs[doc.id].version + 1
        self._docs[doc.id] = doc
        self.lexical.add(doc)
        if doc.embedding:
            self.vector.upsert(doc.id, doc.embedding, metadata={"modality": doc.modality.value})
        return doc

    def remove(self, doc_id: str) -> bool:
        if doc_id not in self._docs:
            return False
        self.lexical.remove(doc_id)
        self.vector.delete(doc_id)
        del self._docs[doc_id]
        return True

    def record_interaction(self, user_id: str, doc_id: str) -> None:
        history = self._user_history[user_id]
        history.append(doc_id)
        if len(history) > 100:
            history = history[-100:]
            self._user_history[user_id] = history

    def search(
        self,
        query: str,
        *,
        user_id: Optional[str] = None,
        modalities: Optional[List[SearchModality]] = None,
        limit: int = 10,
        semantic_weight: float = 0.5,
        lexical_weight: float = 0.4,
        personalization_weight: float = 0.1,
        embedding: Optional[List[float]] = None,
    ) -> List[SearchHit]:
        lexical_results = dict(self.lexical.search(query, k=limit * 4))
        semantic_results: Dict[str, float] = {}
        if embedding is not None:
            for doc_id, score, _meta in self.vector.search(embedding, top_k=limit * 4):
                semantic_results[doc_id] = score

        max_lex = max(lexical_results.values()) if lexical_results else 1.0
        max_sem = max(semantic_results.values()) if semantic_results else 1.0
        personalization = self._user_history.get(user_id or "", [])
        candidate_ids = set(lexical_results) | set(semantic_results)
        hits: List[SearchHit] = []
        for doc_id in candidate_ids:
            doc = self._docs.get(doc_id)
            if doc is None:
                continue
            if modalities and doc.modality not in modalities:
                continue
            lex = lexical_results.get(doc_id, 0.0) / max_lex
            sem = semantic_results.get(doc_id, 0.0) / max_sem
            pscore = 1.0 if doc_id in personalization else 0.0
            score = (
                lex * lexical_weight
                + sem * semantic_weight
                + pscore * personalization_weight
            )
            hits.append(
                SearchHit(
                    doc=doc,
                    score=score,
                    lexical_score=lex,
                    semantic_score=sem,
                    personalization=pscore,
                )
            )
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:limit]

    def stats(self) -> Dict[str, Any]:
        per_modality: Dict[str, int] = defaultdict(int)
        for doc in self._docs.values():
            per_modality[doc.modality.value] += 1
        return {
            "documents": len(self._docs),
            "lexical_terms": len(self.lexical._postings),
            "vectors": self.vector.size(),
            "by_modality": dict(per_modality),
        }


_GLOBAL_SEARCH: Optional[UniversalSearch] = None


def get_universal_search() -> UniversalSearch:
    global _GLOBAL_SEARCH
    if _GLOBAL_SEARCH is None:
        _GLOBAL_SEARCH = UniversalSearch()
    return _GLOBAL_SEARCH