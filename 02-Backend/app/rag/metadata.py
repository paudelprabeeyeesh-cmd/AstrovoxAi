"""Metadata extraction and filtering for RAG pipelines."""

from __future__ import annotations

import hashlib
import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ChunkMetadata:
    chunk_id: str
    document_id: str
    word_count: int = 0
    char_count: int = 0
    language: str = "en"
    keywords: List[str] = field(default_factory=list)
    entities: List[Dict[str, str]] = field(default_factory=list)
    content_hash: str = ""
    sentiment: str = "neutral"
    complexity: str = "simple"
    source_type: str = ""
    filename: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MetadataExtractor:
    """Extract rich metadata from text chunks."""

    STOPWORDS = {
        "the", "and", "is", "of", "to", "in", "that", "for", "with", "as", "on",
        "at", "by", "an", "a", "be", "this", "it", "from", "or", "are", "was",
        "were", "but", "not", "have", "has", "had", "they", "their", "we", "you",
        "i", "he", "she", "his", "her", "its", "our", "your", "my", "me", "us",
        "them", "what", "which", "who", "when", "where", "why", "how", "all",
        "any", "both", "each", "few", "more", "most", "other", "some", "such",
        "than", "too", "very", "can", "will", "just", "into", "out", "up",
    }
    READING_WPM = 200

    def extract(self, text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not text:
            return {"word_count": 0, "char_count": 0}
        words = [w for w in re.findall(r"\b[a-zA-Z]+\b", text) if len(w) > 1]
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        reading_time = round(len(words) / self.READING_WPM, 2)
        language = self._detect_language(text)
        keywords = self._extract_keywords(text)
        entities = self._extract_named_entities(text)
        content_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        sentiment = self._estimate_sentiment(text)
        complexity = self._estimate_complexity(text)
        return {
            "word_count": len(words),
            "char_count": len(text),
            "sentence_count": len(sentences),
            "paragraph_count": len(paragraphs),
            "reading_time_minutes": reading_time,
            "language": language,
            "keywords": keywords,
            "entities": entities,
            "content_hash": content_hash,
            "sentiment": sentiment,
            "complexity": complexity,
            "avg_sentence_length": round(len(words) / max(len(sentences), 1), 1),
            "type_token_ratio": round(len(set(w.lower() for w in words)) / max(len(words), 1), 3),
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            **(context or {}),
        }

    def enrich_chunk_metadata(self, chunk: Any, document_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        meta = self.extract(getattr(chunk, "content", ""), context={
            "chunk_id": getattr(chunk, "id", ""),
            "document_id": getattr(chunk, "document_id", ""),
            "chunk_index": getattr(chunk, "chunk_index", 0),
            "section": getattr(chunk, "section", ""),
        })
        if getattr(chunk, "metadata", None):
            meta.update(chunk.metadata)
        if document_metadata:
            meta["document_metadata"] = document_metadata
        chunk.metadata = meta
        return meta

    @staticmethod
    def _detect_language(text: str) -> str:
        words = set(re.findall(r"\b[a-zà-ÿ]{2,}\b", text.lower()))
        if not words:
            return "en"
        lang_keywords = {
            "en": {"the", "and", "is", "of", "to", "in"},
            "es": {"el", "la", "de", "que", "y"},
            "fr": {"le", "de", "un", "une", "et"},
            "de": {"der", "die", "das", "und", "ist"},
            "it": {"il", "di", "che", "è", "un"},
            "pt": {"o", "a", "de", "que", "e"},
        }
        scores = {lang: len(words & kw) for lang, kw in lang_keywords.items()}
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "en"

    @staticmethod
    def _extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
        words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
        filtered = [w for w in words if w not in MetadataExtractor.STOPWORDS and len(w) >= 4]
        return [w for w, _ in Counter(filtered).most_common(max_keywords)]

    @staticmethod
    def _extract_named_entities(text: str) -> List[Dict[str, str]]:
        entities = []
        caps = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\b", text)
        for name in set(caps):
            if len(name) >= 3 and name.lower() not in MetadataExtractor.STOPWORDS:
                entities.append({"name": name, "type": "PERSON_OR_ORG"})
        emails = re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text)
        for email in set(emails):
            entities.append({"name": email, "type": "EMAIL"})
        return entities[:20]

    @staticmethod
    def _estimate_sentiment(text: str) -> str:
        positive = {"good", "great", "excellent", "amazing", "wonderful", "positive", "love", "best"}
        negative = {"bad", "terrible", "awful", "poor", "negative", "hate", "worst", "fail"}
        words = set(re.findall(r"\b[a-z]+\b", text.lower()))
        pos = len(words & positive)
        neg = len(words & negative)
        if pos > neg:
            return "positive"
        if neg > pos:
            return "negative"
        return "neutral"

    @staticmethod
    def _estimate_complexity(text: str) -> str:
        words = text.split()
        if not words:
            return "simple"
        avg_len = sum(len(w) for w in words) / len(words)
        if avg_len > 7:
            return "complex"
        if avg_len > 5:
            return "moderate"
        return "simple"


class MetadataFilter:
    """Filter documents/chunks by metadata criteria."""

    @staticmethod
    def matches(metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        for key, value in filters.items():
            if key not in metadata:
                return False
            if isinstance(value, list):
                if metadata[key] not in value:
                    return False
            elif metadata[key] != value:
                return False
        return True

    @staticmethod
    def apply(documents: List[Any], filters: Dict[str, Any]) -> List[Any]:
        return [doc for doc in documents if MetadataFilter.matches(getattr(doc, "metadata", {}), filters)]
