"""
Phase B Dataset Validation Module

Validates and cleans datasets for LLM training:
- Token counting and coverage
- Language / domain distribution
- Duplicate detection (exact and near-duplicate)
- Low-quality / corrupted sample removal
- HTML stripping, normalization
- Vocabulary coverage reporting
"""

from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional dependencies
# ---------------------------------------------------------------------------
try:
    from langdetect import DetectorFactory, detect_langs

    DetectorFactory.seed = 0
    _HAS_LANGDETECT = True
except Exception:  # pragma: no cover - optional
    _HAS_LANGDETECT = False
    logger.debug("langdetect not available; language detection disabled")

try:
    from datasketch import MinHash, MinHashLSH

    _HAS_MINHASH = True
except Exception:  # pragma: no cover - optional
    _HAS_MINHASH = False
    logger.debug("datasketch not available; near-duplicate removal disabled")

try:
    import tiktoken

    _HAS_TIKTOKEN = True
except Exception:  # pragma: no cover - optional
    _HAS_TIKTOKEN = False
    logger.debug("tiktoken not available; tokenizer coverage disabled")

try:
    _HAS_TOKENIZERS = True
except Exception:  # pragma: no cover - optional
    _HAS_TOKENIZERS = False
    logger.debug("tokenizers library not available; vocab coverage disabled")

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ValidatedDocument:
    text: str
    source: str = ""
    domain: str = ""
    language: str = ""
    is_corrupted: bool = False
    is_duplicate: bool = False
    is_near_duplicate: bool = False
    is_quality_filtered: bool = False
    quality_reason: str = ""
    token_count: int = 0
    sha256: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "source": self.source,
            "domain": self.domain,
            "language": self.language,
            "is_corrupted": self.is_corrupted,
            "is_duplicate": self.is_duplicate,
            "is_near_duplicate": self.is_near_duplicate,
            "is_quality_filtered": self.is_quality_filtered,
            "quality_reason": self.quality_reason,
            "token_count": self.token_count,
            "sha256": self.sha256,
        }


@dataclass
class ValidationStats:
    total_documents: int = 0
    valid_documents: int = 0
    removed_corrupted: int = 0
    removed_html_only: int = 0
    removed_exact_duplicates: int = 0
    removed_near_duplicates: int = 0
    removed_low_quality: int = 0
    total_tokens: int = 0
    vocab_coverage: float = 0.0
    avg_document_length: float = 0.0
    length_distribution: dict[str, int] = field(default_factory=dict)
    language_distribution: dict[str, int] = field(default_factory=dict)
    domain_distribution: dict[str, int] = field(default_factory=dict)
    vocab_size: int = 0
    unique_tokens: int = 0
    sample_texts: list[str] = field(default_factory=list)

    def merge(self, other: ValidationStats) -> None:
        self.total_documents += other.total_documents
        self.valid_documents += other.valid_documents
        self.removed_corrupted += other.removed_corrupted
        self.removed_html_only += other.removed_html_only
        self.removed_exact_duplicates += other.removed_exact_duplicates
        self.removed_near_duplicates += other.removed_near_duplicates
        self.removed_low_quality += other.removed_low_quality
        self.total_tokens += other.total_tokens
        self.vocab_coverage = max(self.vocab_coverage, other.vocab_coverage)
        self.vocab_size = max(self.vocab_size, other.vocab_size)
        self.unique_tokens = max(self.unique_tokens, other.unique_tokens)

        lengths = list(self.length_distribution.values()) + list(other.length_distribution.values())
        self.avg_document_length = sum(lengths) / len(lengths) if lengths else 0.0

        for lang, count in other.language_distribution.items():
            self.language_distribution[lang] = self.language_distribution.get(lang, 0) + count
        for domain, count in other.domain_distribution.items():
            self.domain_distribution[domain] = self.domain_distribution.get(domain, 0) + count
        self.sample_texts.extend(other.sample_texts[:3])


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class ValidationConfig:
    min_document_length: int = 20
    max_document_length: int = 100_000
    max_special_char_ratio: float = 0.15
    max_repetition_ratio: float = 0.6
    max_repeated_ngram_ratio: float = 0.3
    ngram_size: int = 4
    near_dup_threshold: float = 0.75
    near_dup_num_perm: int = 128
    near_dup_shingle_size: int = 5
    allowed_languages: list[str] = field(default_factory=lambda: ["en"])
    default_language: str = "en"
    language_confidence_threshold: float = 0.5
    tokenizer_name: str = "cl100k_base"
    max_sample_texts: int = 10
    corpus_vocab_path: str | None = None


# ---------------------------------------------------------------------------
# Text utilities
# ---------------------------------------------------------------------------


class TextUtils:
    @staticmethod
    def sha256(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def normalize(text: str) -> str:
        text = unicodedata.normalize("NFKC", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @staticmethod
    def remove_html(text: str) -> str:
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @staticmethod
    def is_corrupted(text: str) -> tuple[bool, str]:
        if not text or not text.strip():
            return True, "empty text"
        if len(text) < 10:
            return True, "text too short"
        null_count = text.count("\x00")
        if null_count > len(text) * 0.1:
            return True, "excessive null bytes"
        return False, ""

    @staticmethod
    def is_html_only(text: str) -> bool:
        cleaned = TextUtils.remove_html(text)
        return bool(re.fullmatch(r"[\s]*", cleaned))

    @staticmethod
    def special_char_ratio(text: str) -> float:
        if not text:
            return 0.0
        special = sum(1 for c in text if not c.isalnum() and not c.isspace())
        return special / len(text)

    @staticmethod
    def repetition_ratio(text: str, ngram_size: int = 4) -> float:
        tokens = re.findall(r"\w+", text.lower())
        if len(tokens) < ngram_size:
            return 0.0
        ngrams = [tuple(tokens[i : i + ngram_size]) for i in range(len(tokens) - ngram_size + 1)]
        counts = Counter(ngrams)
        repeated = sum(c - 1 for c in counts.values() if c > 1)
        return repeated / len(ngrams) if ngrams else 0.0

    @staticmethod
    def token_count(text: str, tokenizer_name: str = "cl100k_base") -> int:
        if _HAS_TIKTOKEN:
            try:
                enc = tiktoken.get_encoding(tokenizer_name)
                return len(enc.encode(text))
            except Exception:
                pass
        return len(text.split())


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------


class DuplicateDetector:
    def __init__(self, config: ValidationConfig) -> None:
        self.config = config
        self.seen_hashes: set = set()
        self.lsh = None
        if _HAS_MINHASH:
            self.lsh = MinHashLSH(
                threshold=config.near_dup_threshold,
                num_perm=config.near_dup_num_perm,
            )
        self.removed_exact = 0
        self.removed_near = 0

    def _minhash(self, text: str) -> Any | None:
        if not _HAS_MINHASH or self.lsh is None:
            return None
        m = MinHash(num_perm=self.config.near_dup_num_perm)
        for shingle in TextUtils.shingles(text, self.config.near_dup_shingle_size):
            m.update(shingle.encode("utf-8"))
        return m

    def is_duplicate(self, text: str, sha: str) -> tuple[bool, bool]:
        normalized = TextUtils.normalize(text)
        doc_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()

        if doc_hash in self.seen_hashes:
            self.removed_exact += 1
            return True, False

        self.seen_hashes.add(doc_hash)

        if self.lsh is not None:
            m = self._minhash(normalized)
            if m is not None:
                matches = self.lsh.query(m)
                if matches:
                    self.removed_near += 1
                    return False, True
                self.lsh.insert(doc_hash, m)

        return False, False

    @staticmethod
    def shingles(text: str, size: int = 5) -> Iterator[str]:
        tokens = re.findall(r"\w+", text.lower())
        if len(tokens) < size:
            yield " ".join(tokens)
            return
        for i in range(len(tokens) - size + 1):
            yield " ".join(tokens[i : i + size])


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------


class LanguageDetector:
    def __init__(self, config: ValidationConfig) -> None:
        self.config = config

    def detect(self, text: str) -> tuple[str, float]:
        if not _HAS_LANGDETECT:
            return self.config.default_language, 0.0
        try:
            langs = detect_langs(text[:1000])
            if not langs:
                return self.config.default_language, 0.0
            best = langs[0]
            return best.lang, best.prob
        except Exception:
            return self.config.default_language, 0.0

    def is_allowed(self, text: str) -> tuple[bool, str]:
        lang, confidence = self.detect(text)
        if confidence < self.config.language_confidence_threshold:
            lang = self.config.default_language
        return lang in self.config.allowed_languages, lang


# ---------------------------------------------------------------------------
# Low-quality filter
# ---------------------------------------------------------------------------


class QualityFilter:
    def __init__(self, config: ValidationConfig) -> None:
        self.config = config

    def is_low_quality(self, text: str) -> tuple[bool, str]:
        length = len(text.split())
        if length < self.config.min_document_length:
            return True, f"too short ({length} words)"
        if length > self.config.max_document_length:
            return True, f"too long ({length} words)"

        special_ratio = TextUtils.special_char_ratio(text)
        if special_ratio > self.config.max_special_char_ratio:
            return True, f"too many special characters ({special_ratio:.2f})"

        repetition = TextUtils.repetition_ratio(text, self.config.ngram_size)
        if repetition > self.config.max_repeated_ngram_ratio:
            return True, f"too repetitive ({repetition:.2f})"

        return False, ""


# ---------------------------------------------------------------------------
# Tokenizer coverage
# ---------------------------------------------------------------------------


class TokenizerCoverage:
    def __init__(self, config: ValidationConfig) -> None:
        self.config = config
        self.vocab: set = set()
        if config.corpus_vocab_path and Path(config.corpus_vocab_path).exists():
            try:
                with open(config.corpus_vocab_path, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            self.vocab.add(line)
            except Exception as exc:
                logger.warning("Failed to load corpus vocab: %s", exc)

    def compute_coverage(self, text: str) -> tuple[float, int, int]:
        if not _HAS_TIKTOKEN or not self.vocab:
            return 100.0, TextUtils.token_count(text, self.config.tokenizer_name), 0
        try:
            enc = tiktoken.get_encoding(self.config.tokenizer_name)
            tokens = enc.encode(text)
            total = len(tokens)
            in_vocab = sum(1 for t in tokens if enc.decode([t]).strip() in self.vocab)
            coverage = in_vocab / total if total > 0 else 100.0
            return coverage * 100.0, total, in_vocab
        except Exception:
            return 100.0, TextUtils.token_count(text, self.config.tokenizer_name), 0


# ---------------------------------------------------------------------------
# Sentence duplicate detection
# ---------------------------------------------------------------------------


class SentenceDuplicateDetector:
    def __init__(self) -> None:
        self.seen_sentences: set = set()
        self.removed = 0

    def has_duplicate_sentence(self, text: str) -> bool:
        sentences = re.split(r"[.!?]+", text)
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            normalized = TextUtils.normalize(sentence)
            sha = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
            if sha in self.seen_sentences:
                self.removed += 1
                return True
            self.seen_sentences.add(sha)
        return False


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


class DatasetValidator:
    def __init__(self, config: ValidationConfig | None = None) -> None:
        self.config = config or ValidationConfig()
        self.dup_detector = DuplicateDetector(self.config)
        self.lang_detector = LanguageDetector(self.config)
        self.quality_filter = QualityFilter(self.config)
        self.tokenizer_coverage = TokenizerCoverage(self.config)
        self.sent_dedup = SentenceDuplicateDetector()
        self.stats = ValidationStats()

    def _process(self, text: str, source: str = "", domain: str = "") -> ValidatedDocument | None:
        self.stats.total_documents += 1
        text = text.strip()
        if not text:
            self.stats.removed_corrupted += 1
            return None

        if TextUtils.is_html_only(text):
            self.stats.removed_html_only += 1
            return None

        text = TextUtils.remove_html(text)

        corrupted, reason = TextUtils.is_corrupted(text)
        if corrupted:
            logger.debug("Corrupted document removed: %s", reason)
            self.stats.removed_corrupted += 1
            return None

        allowed, lang = self.lang_detector.is_allowed(text)
        if not allowed:
            logger.debug("Document removed: language not allowed (%s)", lang)
            return None

        sha = TextUtils.sha256(text)
        is_dup, is_near = self.dup_detector.is_duplicate(text, sha)
        if is_dup:
            self.stats.removed_exact_duplicates += 1
            doc = ValidatedDocument(
                text=text,
                source=source,
                domain=domain,
                language=lang,
                is_duplicate=True,
                sha256=sha,
            )
            return doc
        if is_near:
            self.stats.removed_near_duplicates += 1
            doc = ValidatedDocument(
                text=text,
                source=source,
                domain=domain,
                language=lang,
                is_near_duplicate=True,
                sha256=sha,
            )
            return doc

        if self.sent_dedup.has_duplicate_sentence(text):
            return None

        is_low, reason = self.quality_filter.is_low_quality(text)
        if is_low:
            logger.debug("Low-quality document removed: %s", reason)
            self.stats.removed_low_quality += 1
            doc = ValidatedDocument(
                text=text,
                source=source,
                domain=domain,
                language=lang,
                is_quality_filtered=True,
                quality_reason=reason,
                sha256=sha,
            )
            return doc

        coverage, token_count, in_vocab = self.tokenizer_coverage.compute_coverage(text)
        doc = ValidatedDocument(
            text=text,
            source=source,
            domain=domain,
            language=lang,
            token_count=token_count,
            sha256=sha,
        )
        self.stats.valid_documents += 1
        self.stats.total_tokens += token_count
        self.stats.vocab_coverage = coverage
        self.stats.unique_tokens = in_vocab
        self.stats.domain_distribution[domain or "general"] = (
            self.stats.domain_distribution.get(domain or "general", 0) + 1
        )
        self.stats.language_distribution[lang] = self.stats.language_distribution.get(lang, 0) + 1

        length_bucket = self._length_bucket(text)
        self.stats.length_distribution[length_bucket] = (
            self.stats.length_distribution.get(length_bucket, 0) + 1
        )

        if len(self.stats.sample_texts) < self.config.max_sample_texts:
            self.stats.sample_texts.append(text[:500])

        return doc

    def _length_bucket(self, text: str) -> str:
        words = len(text.split())
        if words < 50:
            return "<50"
        if words < 200:
            return "50-200"
        if words < 500:
            return "200-500"
        if words < 1000:
            return "500-1k"
        if words < 5000:
            return "1k-5k"
        return "5k+"

    def process_document(
        self, text: str, source: str = "", domain: str = ""
    ) -> ValidatedDocument | None:
        return self._process(text, source, domain)

    def process_stream(
        self,
        documents: Iterable[tuple[str, str, str]],
    ) -> ValidationStats:
        self.stats = ValidationStats()
        for text, source, domain in documents:
            self.process_document(text, source, domain)
        self._finalize()
        return self.stats

    def _finalize(self) -> None:
        if self.stats.valid_documents > 0:
            self.stats.avg_document_length = self.stats.total_tokens / self.stats.valid_documents

    def reset(self) -> None:
        self.dup_detector = DuplicateDetector(self.config)
        self.sent_dedup = SentenceDuplicateDetector()
        self.stats = ValidationStats()


def validate_dataset(
    documents: Iterable[tuple[str, str, str]],
    config: ValidationConfig | None = None,
) -> ValidationStats:
    validator = DatasetValidator(config)
    return validator.process_stream(documents)
