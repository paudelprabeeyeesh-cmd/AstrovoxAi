from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from models.llm.dataset_engineering_v2 import ProcessedDocument, TextUtils

logger = logging.getLogger(__name__)


@dataclass
class CopyrightConfig:
    enabled: bool = True
    copyright_phrases: list[str] = field(
        default_factory=lambda: [
            "all rights reserved",
            "copyright ",
            "licensed under",
            "published by",
            "isbn",
            "terms of service",
            "privacy policy",
        ]
    )
    max_copyright_matches: int = 2


class CopyrightFilter:
    def __init__(self, config: CopyrightConfig | None = None) -> None:
        self.config = config or CopyrightConfig()
        self.removed = 0
        self._patterns = [
            re.compile(re.escape(p), re.IGNORECASE) for p in self.config.copyright_phrases
        ]

    def _score(self, text: str) -> float:
        matches = 0
        for pattern in self._patterns:
            if pattern.search(text):
                matches += 1
        tokens = len(re.findall(r"\w+", text))
        if tokens == 0:
            return 1.0 if matches > 0 else 0.0
        return matches / (tokens * 0.05)

    def process(self, document: ProcessedDocument) -> ProcessedDocument | None:
        if not self.config.enabled:
            return document
        score = self._score(document.text)
        if score > self.config.max_copyright_matches:
            self.removed += 1
            logger.debug("Copyright filter removed doc with score %.2f", score)
            return None
        return document


@dataclass
class PiiConfig:
    enabled: bool = True
    strip_email: bool = True
    strip_phone: bool = True
    strip_ip: bool = True
    strip_ssn: bool = True
    strip_credit_card: bool = True
    strip_iban: bool = True
    replacement: str = "[REDACTED]"


class PIIDetector:
    _EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    _PHONE_RE = re.compile(r"(?:(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})")
    _IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
    _SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
    _CREDIT_CARD_RE = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b|\b\d{13,16}\b")
    _IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{1,30}\b")

    def __init__(self, config: PiiConfig | None = None) -> None:
        self.config = config or PiiConfig()
        self.removed_count = 0

    def _replace(self, text: str) -> tuple[str, bool]:
        original = text
        if self.config.strip_email:
            text = self._EMAIL_RE.sub(self.config.replacement, text)
        if self.config.strip_phone:
            text = self._PHONE_RE.sub(self.config.replacement, text)
        if self.config.strip_ip:
            text = self._IP_RE.sub(self.config.replacement, text)
        if self.config.strip_ssn:
            text = self._SSN_RE.sub(self.config.replacement, text)
        if self.config.strip_credit_card:
            text = self._CREDIT_CARD_RE.sub(self.config.replacement, text)
        if self.config.strip_iban:
            text = self._IBAN_RE.sub(self.config.replacement, text)
        return text, text != original

    def process(self, document: ProcessedDocument) -> ProcessedDocument:
        if not self.config.enabled:
            return document
        cleaned, changed = self._replace(document.text)
        document.text = cleaned
        document.pii_removed = changed
        if changed:
            self.removed_count += 1
        return document


@dataclass
class ToxicityConfig:
    enabled: bool = True
    max_toxicity_score: float = 0.3
    profanity_tokens: list[str] = field(
        default_factory=lambda: [
            "fuck",
            "shit",
            "bitch",
            "cunt",
            "nigga",
            "nigger",
            "chink",
            "spic",
            "kike",
            "retard",
            "rape",
        ]
    )


class ToxicityFilter:
    def __init__(self, config: ToxicityConfig | None = None) -> None:
        self.config = config or ToxicityConfig()
        self.removed = 0
        pattern = r"\b(" + "|".join(re.escape(t) for t in self.config.profanity_tokens) + r")\b"
        self._regex = re.compile(pattern, re.IGNORECASE)

    def _score(self, text: str) -> float:
        matches = self._regex.findall(text)
        tokens = len(re.findall(r"\w+", text))
        if tokens == 0:
            return 1.0 if matches else 0.0
        return min(1.0, len(matches) / (tokens * 0.1))

    def process(self, document: ProcessedDocument) -> ProcessedDocument | None:
        if not self.config.enabled:
            return document
        score = self._score(document.text)
        if score > self.config.max_toxicity_score:
            self.removed += 1
            return None
        return document


@dataclass
class DedupConfig:
    enabled: bool = True
    max_near_dup_threshold: float = 0.8
    shingle_size: int = 5


class Deduplicator:
    def __init__(self, config: DedupConfig | None = None) -> None:
        self.config = config or DedupConfig()
        self.seen_hashes: set[str] = set()
        self.seen_shingles: list[set[str]] = []
        self.removed_exact = 0
        self.removed_near = 0

    def _shingles(self, text: str) -> list[str]:
        tokens = re.findall(r"\w+", text.lower())
        size = self.config.shingle_size
        if len(tokens) < size:
            return [" ".join(tokens)]
        return [" ".join(tokens[i : i + size]) for i in range(len(tokens) - size + 1)]

    def _jaccard(self, a: set[str], b: set[str]) -> float:
        if not a or not b:
            return 0.0
        intersection = len(a & b)
        union = len(a | b)
        return intersection / union if union > 0 else 0.0

    def process(
        self, document: ProcessedDocument
    ) -> ProcessedDocument:
        if not self.config.enabled:
            return document
        normalized = TextUtils.normalize(document.text)
        doc_hash = TextUtils.sha256(normalized)
        if doc_hash in self.seen_hashes:
            self.removed_exact += 1
            document.dedup_hash = doc_hash
            document.metadata["duplicate"] = "exact"
            return document
        shingle_set = set(self._shingles(normalized))
        for existing_shingles in self.seen_shingles:
            if self._jaccard(shingle_set, existing_shingles) > self.config.max_near_dup_threshold:
                self.removed_near += 1
                document.dedup_hash = doc_hash
                document.metadata["duplicate"] = "near"
                return document
        self.seen_hashes.add(doc_hash)
        self.seen_shingles.append(shingle_set)
        document.dedup_hash = doc_hash
        return document

    def process_stream(
        self, documents: list[ProcessedDocument]
    ) -> tuple[list[ProcessedDocument], list[ProcessedDocument]]:
        kept: list[ProcessedDocument] = []
        removed: list[ProcessedDocument] = []
        for doc in documents:
            result = self.process(doc)
            if "duplicate" in result.metadata:
                removed.append(result)
            else:
                kept.append(result)
        return kept, removed
