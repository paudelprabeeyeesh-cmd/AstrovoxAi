"""
Phase 2 Multilingual Dataset Engineering Pipeline v2

Complete pipeline for ingesting, cleaning, deduplicating, and processing
multilingual text datasets from multiple sources with enhanced filtering,
language detection, quality scoring, domain balancing, and versioning.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import random
import re
import time
import unicodedata
import uuid
from collections import Counter
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional dependencies with graceful fallbacks
# ---------------------------------------------------------------------------
try:
    from datasketch import MinHash, MinHashLSH

    _HAS_MINHASH = True
except Exception:  # pragma: no cover - optional
    _HAS_MINHASH = False
    logger.debug("datasketch not available; MinHash dedup disabled")

try:
    import simhash

    _HAS_SIMHASH = True
except Exception:  # pragma: no cover - optional
    _HAS_SIMHASH = False
    logger.debug("simhash not available; SimHash dedup disabled")

try:
    from pybloom_live import ScalableBloomFilter

    _HAS_BLOOM = True
except Exception:  # pragma: no cover - optional
    _HAS_BLOOM = False
    logger.debug("pybloom-live not available; Bloom filter dedup disabled")

try:
    from langdetect import DetectorFactory, detect_langs

    DetectorFactory.seed = 0
    _HAS_LANGDETECT = True
except Exception:  # pragma: no cover - optional
    _HAS_LANGDETECT = False
    logger.debug("langdetect not available; language detection disabled")

try:
    import pyarrow.parquet as pq

    _HAS_PYARROW = True
except Exception:  # pragma: no cover - optional
    _HAS_PYARROW = False
    logger.debug("pyarrow not available; parquet support disabled")

try:
    import ijson

    _HAS_IJSON = True
except Exception:  # pragma: no cover - optional
    _HAS_IJSON = False
    logger.debug("ijson not available; JSON streaming disabled")

try:
    import tiktoken

    _HAS_TIKTOKEN = True
except Exception:  # pragma: no cover - optional
    _HAS_TIKTOKEN = False
    logger.debug("tiktoken not available; token counting disabled")

try:

    _HAS_PANDAS = True
except Exception:  # pragma: no cover - optional
    _HAS_PANDAS = False
    logger.debug("pandas not available; some analytics disabled")

try:
    from datasets import load_dataset

    _HAS_DATASETS = True
except Exception:  # pragma: no cover - optional
    _HAS_DATASETS = False
    logger.debug("datasets not available; HF streaming disabled")

try:

    _HAS_EASYOCR = False
except Exception:  # pragma: no cover - optional
    _HAS_EASYOCR = False

try:

    _HAS_PIL = True
except Exception:  # pragma: no cover - optional
    _HAS_PIL = False
    logger.debug("PIL not available; image processing disabled")

try:

    _HAS_REQUESTS = True
except Exception:  # pragma: no cover - optional
    _HAS_REQUESTS = False
    logger.debug("requests not available; web fetching disabled")

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ProcessedDocument:
    text: str
    source: str = ""
    domain: str = ""
    quality_score: float = 0.0
    language: str = ""
    language_confidence: float = 0.0
    pii_removed: bool = False
    dedup_hash: str = ""
    simhash: int = 0
    token_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DatasetStats:
    total_documents: int = 0
    kept_documents: int = 0
    removed_exact_duplicates: int = 0
    removed_near_duplicates: int = 0
    removed_toxicity: int = 0
    removed_pii: int = 0
    removed_quality: int = 0
    removed_language: int = 0
    removed_bloom: int = 0
    domains: dict[str, int] = field(default_factory=dict)
    languages: dict[str, int] = field(default_factory=Counter)
    token_stats: dict[str, float] = field(default_factory=dict)
    processing_time_seconds: float = 0.0
    dataset_version: str = ""

    def merge(self, other: DatasetStats) -> None:
        self.total_documents += other.total_documents
        self.kept_documents += other.kept_documents
        self.removed_exact_duplicates += other.removed_exact_duplicates
        self.removed_near_duplicates += other.removed_near_duplicates
        self.removed_toxicity += other.removed_toxicity
        self.removed_pii += other.removed_pii
        self.removed_quality += other.removed_quality
        self.removed_language += other.removed_language
        self.removed_bloom += other.removed_bloom
        for domain, count in other.domains.items():
            self.domains[domain] = self.domains.get(domain, 0) + count
        self.languages.update(other.languages)
        self.processing_time_seconds += other.processing_time_seconds


@dataclass
class DatasetVersion:
    version: str
    created_at: str
    source: str
    documents_count: int
    tokens_count: int
    config_snapshot: dict[str, Any] = field(default_factory=dict)
    checksum: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "created_at": self.created_at,
            "source": self.source,
            "documents_count": self.documents_count,
            "tokens_count": self.tokens_count,
            "config_snapshot": self.config_snapshot,
            "checksum": self.checksum,
        }


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class DedupConfig:
    enabled: bool = True
    exact_hash_field: str = "text"
    near_duplicate: bool = True
    near_dup_method: str = "minhash"  # minhash | simhash
    near_dup_threshold: float = 0.75
    near_dup_shingle_size: int = 5
    near_dup_num_perm: int = 128
    use_bloom_filter: bool = True
    bloom_capacity: int = 10_000_000
    bloom_error_rate: float = 0.001


@dataclass
class ToxicityConfig:
    enabled: bool = True
    max_toxicity_score: float = 0.3
    multilingual_profanity: bool = True
    profanity_tokens: list[str] = field(
        default_factory=lambda: [
            "fuck",
            "shit",
            "ass",
            "bitch",
            "cunt",
            "dick",
            "piss",
            "twat",
            "wank",
            "nigga",
            "nigger",
            "chink",
            "spic",
            "kike",
            "retard",
            "rape",
            "puta",
            "mierda",
            "cabron",
            "joder",
            "coño",
            "hostia",
            "verg",
            "scheisse",
            "hurensohn",
            "wichser",
            "fotze",
            "arsch",
            "pute",
            "merde",
            "putain",
            "connard",
            "salope",
            "bordel",
            "cul",
            "cazzo",
            "stronzo",
            "vaffanculo",
            "porco",
            "puttana",
            "kurwa",
            "chuj",
            "jebaniec",
            "pizda",
            "suka",
            "blyat",
            "pizd",
            "хер",
            "пизд",
            "сука",
            "блядь",
            "ебать",
            "гандон",
            "хуй",
            "шлюха",
            "бля",
            "еб",
            "пиз",
            "ху",
            "ганд",
            "шлю",
            "ебан",
            "нахуй",
            "нахуя",
            "ёб",
            "бляд",
            "херня",
            "пиздец",
            "ёбаный",
            "хуета",
            "ебана",
            "пиздобол",
            "пиздатый",
            "пиздёныш",
            "пиздеть",
            "пиздеть",
            "хрен",
            "хреновый",
            "хуёво",
            "ёбнутый",
            "ёбнуться",
            "ёбнись",
            "ёбанный",
            "ёбка",
            "ёб",
            "ёб",
            "пизда",
            "пизда",
            "пизда",
            "пизда",
            "пизда",
        ]
    )


@dataclass
class QualityConfig:
    enabled: bool = True
    min_quality_score: float = 0.2
    use_perplexity: bool = True
    perplexity_model: str | None = None
    length_normalization: bool = True
    diversity_weight: float = 0.3
    min_length: int = 20
    max_length: int = 100_000
    min_alpha_ratio: float = 0.5
    max_url_ratio: float = 0.3
    max_repeated_chars: int = 10
    max_repeated_words: int = 5


@dataclass
class LanguageConfig:
    enabled: bool = True
    allowed_languages: list[str] = field(
        default_factory=lambda: [
            "en",
            "es",
            "fr",
            "de",
            "it",
            "pt",
            "ru",
            "zh",
            "ja",
            "ko",
            "ar",
            "hi",
            "bn",
            "pa",
            "jv",
            "pa",
            "tr",
            "vi",
            "th",
            "id",
            "ms",
            "cs",
            "pl",
            "nl",
            "sv",
            "da",
            "no",
            "fi",
            "el",
            "he",
            "ro",
            "hu",
            "uk",
            "bg",
            "hr",
            "sr",
            "sk",
            "sl",
            "lt",
            "lv",
            "et",
            "tl",
            "sw",
            "zu",
            "af",
            "ka",
            "hy",
            "az",
            "kk",
            "uz",
            "mn",
            "my",
            "km",
            "lo",
            "ne",
            "si",
            "ta",
            "te",
            "kn",
            "ml",
            "mr",
            "gu",
            "ur",
            "fa",
            "ps",
            "ku",
            "am",
            "so",
            "rw",
            "yo",
            "ig",
            "ha",
            "eu",
            "gl",
            "ca",
            "cy",
            "is",
            "ga",
            "mt",
            "sq",
            "mk",
            "be",
            "ky",
            "tg",
            "tk",
            "tt",
            "ba",
            "cv",
            "ch",
            "ce",
            "os",
            "sah",
            "mhr",
            "myv",
            "udm",
            "mdf",
            "koi",
            "kum",
            "nog",
            "kbd",
            "ady",
            "ab",
            "av",
            "le",
            "lbe",
            "tab",
            "tly",
            "t",
            "dv",
            "ff",
            "bm",
            "tn",
            "ts",
            "ve",
            "nr",
            "ss",
            "st",
            "tn",
            "xh",
            "zu",
            "sn",
            "yo",
            "ha",
            "ig",
            "kr",
            "tw",
            "ee",
            "fon",
            "ln",
            "kg",
            "lg",
            "lu",
            "rw",
            "rn",
            "ik",
            "iu",
            "oj",
            "cr",
            "chr",
            "nv",
            "ht",
            "ay",
            "qu",
            "gn",
            "cbk",
            "ia",
            "eo",
            "vo",
            "jbo",
            "lfn",
            "nov",
            "tok",
            "ido",
            "ie",
            "alt",
            "bxr",
            "ruq",
            "rue",
            "be-x-old",
            "mhr",
            "mwl",
            "dsb",
            "hsb",
            "gsw",
            "pdc",
            "gcr",
            "frp",
            "oc",
            "co",
            "sc",
            "rm",
            "fur",
            "lij",
            "nap",
            "scn",
            "vec",
            "lad",
            "it",
            "la",
            "grc",
            "enm",
            "ang",
            "non",
            "goh",
            "osx",
            "fro",
            "frp",
            "wa",
            "pms",
            "ast",
            "ext",
            "mwl",
            "roa-opt",
            "roa-tara",
            "vec",
            "lad",
            "rup",
            "ruq",
            "rue",
            "be-x-old",
        ]
    )
    default_language: str = "en"
    confidence_threshold: float = 0.5
    multilingual_toxicity: bool = True


@dataclass
class PiiConfig:
    enabled: bool = True
    strip_email: bool = True
    strip_phone: bool = True
    strip_ip: bool = True
    strip_ssn: bool = True
    strip_credit_card: bool = True
    strip_iban: bool = True
    strip_medical: bool = False
    replacement: str = "[REDACTED]"


@dataclass
class DomainBalanceConfig:
    enabled: bool = True
    target_ratios: dict[str, float] = field(
        default_factory=lambda: {
            "web": 0.30,
            "wiki": 0.10,
            "books": 0.10,
            "academic": 0.10,
            "code": 0.10,
            "math": 0.05,
            "qa": 0.05,
            "conversations": 0.10,
            "ocr": 0.05,
            "image_caption": 0.05,
            "multilingual": 0.10,
        }
    )
    buffer_size: int = 100_000


@dataclass
class IngestionConfig:
    output_dir: str = "data/processed"
    cache_dir: str = "data/cache"
    raw_dir: str = "data/raw"
    version: str = "v1"
    streaming_chunk_size: int = 10_000
    max_documents_per_source: int | None = None
    incremental: bool = False
    resume: bool = True
    checkpoint_interval: int = 50_000


@dataclass
class DatasetEngineeringConfig:
    dedup: DedupConfig = field(default_factory=DedupConfig)
    toxicity: ToxicityConfig = field(default_factory=ToxicityConfig)
    quality: QualityConfig = field(default_factory=QualityConfig)
    language: LanguageConfig = field(default_factory=LanguageConfig)
    pii: PiiConfig = field(default_factory=PiiConfig)
    domain_balance: DomainBalanceConfig = field(default_factory=DomainBalanceConfig)
    ingestion: IngestionConfig = field(default_factory=IngestionConfig)
    domain: str = "general"
    source: str = "unknown"
    seed: int = 42


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
        text = text.lower()
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @staticmethod
    def shingles(text: str, size: int = 5) -> Iterator[str]:
        tokens = re.findall(r"\w+", text.lower())
        if len(tokens) < size:
            yield " ".join(tokens)
            return
        for i in range(len(tokens) - size + 1):
            yield " ".join(tokens[i : i + size])

    @staticmethod
    def type_token_ratio(text: str) -> float:
        tokens = re.findall(r"\w+", text.lower())
        if not tokens:
            return 0.0
        unique = len(set(tokens))
        return unique / len(tokens)

    @staticmethod
    def count_tokens(text: str, model: str = "cl100k_base") -> int:
        if not _HAS_TIKTOKEN:
            return len(text.split())
        try:
            enc = tiktoken.get_encoding(model)
            return len(enc.encode(text))
        except Exception:
            return len(text.split())

    @staticmethod
    def clean_text(text: str) -> str:
        if not isinstance(text, str):
            return ""
        text = unicodedata.normalize("NFKC", text)
        text = re.sub(r"\r\n", "\n", text)
        text = re.sub(r"\r", "\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"https?://\S+|www\.\S+", " ", text)
        text = re.sub(r"[^\w\s.,!?;:'\"\-\(\)\[\]\{\}]", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def simhash_value(text: str) -> int:
        if _HAS_SIMHASH:
            try:
                return int(simhash.simhash(text))
            except Exception:
                pass
        # Fallback: use a simplified hash-based simhash
        bits = 64
        v = [0] * bits
        tokens = re.findall(r"\w+", text.lower())
        for token in tokens:
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            for i in range(bits):
                if h & (1 << i):
                    v[i] += 1
                else:
                    v[i] -= 1
        fingerprint = 0
        for i in range(bits):
            if v[i] > 0:
                fingerprint |= 1 << i
        return fingerprint

    @staticmethod
    def hamming_distance(h1: int, h2: int) -> int:
        return bin(h1 ^ h2).count("1")


# ---------------------------------------------------------------------------
# Deduplication (enhanced with MinHash, SimHash, Bloom)
# ---------------------------------------------------------------------------


class Deduplicator:
    def __init__(self, config: DedupConfig) -> None:
        self.config = config
        self.seen_hashes: set[str] = set()
        self.lsh: Any | None = None
        if config.enabled and config.near_duplicate and _HAS_MINHASH:
            try:
                self.lsh = MinHashLSH(
                    threshold=config.near_dup_threshold,
                    num_perm=config.near_dup_num_perm,
                )
            except Exception as exc:
                logger.warning("Failed to initialize MinHashLSH: %s", exc)
                self.lsh = None
        self.bloom_filter: Any | None = None
        if config.enabled and config.use_bloom_filter and _HAS_BLOOM:
            try:
                self.bloom_filter = ScalableBloomFilter(
                    mode=ScalableBloomFilter.SMALL_SET_GROWTH,
                    initial_capacity=config.bloom_capacity,
                    error_rate=config.bloom_error_rate,
                )
            except Exception as exc:
                logger.warning("Failed to initialize Bloom filter: %s", exc)
                self.bloom_filter = None
        self.removed_exact = 0
        self.removed_near = 0
        self.removed_bloom = 0

    def _minhash(self, text: str) -> Any | None:
        if not _HAS_MINHASH or self.lsh is None:
            return None
        try:
            m = MinHash(num_perm=self.config.near_dup_num_perm)
            for shingle in TextUtils.shingles(text, self.config.near_dup_shingle_size):
                m.update(shingle.encode("utf-8"))
            return m
        except Exception as exc:
            logger.debug("MinHash computation failed: %s", exc)
            return None

    def process(self, document: ProcessedDocument) -> ProcessedDocument | None:
        if not self.config.enabled:
            return document

        text = getattr(document, self.config.exact_hash_field, document.text)
        normalized = TextUtils.normalize(text)
        doc_hash = TextUtils.sha256(normalized)

        if doc_hash in self.seen_hashes:
            self.removed_exact += 1
            return None

        if self.bloom_filter is not None:
            try:
                if doc_hash in self.bloom_filter:
                    self.removed_bloom += 1
                    return None
                self.bloom_filter.add(doc_hash)
            except Exception as exc:
                logger.debug("Bloom filter check failed: %s", exc)

        self.seen_hashes.add(doc_hash)

        if self.lsh is not None:
            m = self._minhash(normalized)
            if m is not None:
                try:
                    matches = self.lsh.query(m)
                    if matches:
                        self.removed_near += 1
                        return None
                    self.lsh.insert(doc_hash, m)
                except Exception as exc:
                    logger.debug("MinHash LSH query failed: %s", exc)

        if self.config.near_dup_method == "simhash" and _HAS_SIMHASH:
            try:
                document.simhash = TextUtils.simhash_value(normalized)
            except Exception as exc:
                logger.debug("SimHash computation failed: %s", exc)

        document.dedup_hash = doc_hash
        return document


# ---------------------------------------------------------------------------
# Toxicity filtering (multilingual)
# ---------------------------------------------------------------------------


class ToxicityFilter:
    def __init__(self, config: ToxicityConfig) -> None:
        self.config = config
        self.removed = 0
        self._multilingual_patterns: dict[str, list[str]] = {
            "es": ["puta", "mierda", "cabron", "joder", "coño", "hostia", "verg"],
            "fr": ["pute", "merde", "putain", "connard", "salope", "bordel", "cul"],
            "de": ["scheisse", "hurensohn", "wichser", "fotze", "arsch"],
            "it": ["cazzo", "stronzo", "vaffanculo", "porco", "puttana"],
            "pl": ["kurwa", "chuj", "jebaniec", "pizda"],
            "ru": ["сука", "блядь", "ебать", "гандон", "хуй", "шлюха", "бля"],
            "pt": ["puta", "caralho", "merda", "filho da puta", "vai se foder"],
        }
        self._compiled: dict[str, re.Pattern] = {}
        for lang, tokens in self._multilingual_patterns.items():
            pattern = r"\b(" + "|".join(re.escape(t) for t in tokens) + r")\b"
            self._compiled[lang] = re.compile(pattern, re.IGNORECASE)
        pattern = r"\b(" + "|".join(re.escape(t) for t in config.profanity_tokens) + r")\b"
        self._default_regex = re.compile(pattern, re.IGNORECASE)

    def _score(self, text: str, language: str = "en") -> float:
        matches: list[str] = []
        regex = self._compiled.get(language, self._default_regex)
        try:
            matches = regex.findall(text)
        except Exception:
            matches = self._default_regex.findall(text)
        if not matches:
            return 0.0
        tokens = len(re.findall(r"\w+", text))
        if tokens == 0:
            return 1.0
        return min(1.0, len(matches) / (tokens * 0.1))

    def process(self, document: ProcessedDocument) -> ProcessedDocument | None:
        if not self.config.enabled:
            return document
        score = self._score(document.text, document.language or "en")
        if score > self.config.max_toxicity_score:
            self.removed += 1
            return None
        return document


# ---------------------------------------------------------------------------
# Quality scoring
# ---------------------------------------------------------------------------


class QualityScorer:
    def __init__(self, config: QualityConfig) -> None:
        self.config = config
        self.enc = None
        if config.use_perplexity and _HAS_TIKTOKEN:
            try:
                self.enc = tiktoken.get_encoding("cl100k_base")
            except Exception:
                logger.debug("Failed to load tiktoken encoding")

    def _perplexity(self, text: str) -> float:
        if self.enc is None:
            return 50.0
        try:
            tokens = self.enc.encode(text)
            if len(tokens) < 2:
                return 100.0
            entropy = 0.0
            for i in range(1, len(tokens)):
                prev = tokens[i - 1]
                curr = tokens[i]
                entropy += abs(curr - prev)
            entropy /= len(tokens)
            return min(200.0, max(1.0, entropy))
        except Exception:
            return 50.0

    def _check_quality(self, text: str) -> tuple[bool, float]:
        length = len(text.split())
        if length < self.config.min_length or length > self.config.max_length:
            return False, 0.0

        length_score = 1.0
        if self.config.length_normalization:
            ideal = 200
            length_score = math.exp(-((length - ideal) ** 2) / (2 * (ideal**2)))

        alpha_count = sum(1 for c in text if c.isalpha())
        alpha_ratio = alpha_count / max(len(text), 1)
        if alpha_ratio < self.config.min_alpha_ratio:
            return False, 0.0

        url_count = len(re.findall(r"https?://\S+", text))
        if url_count / max(len(text.split()), 1) > self.config.max_url_ratio:
            return False, 0.0

        for char in set(text):
            if text.count(char) > self.config.max_repeated_chars:
                return False, 0.0

        words = text.split()
        word_counts = Counter(words)
        if any(count > self.config.max_repeated_words for count in word_counts.values()):
            return False, 0.0

        diversity_score = TextUtils.type_token_ratio(text)
        perplexity = self._perplexity(text)
        perplexity_score = max(0.0, min(1.0, 1.0 - (perplexity / 200.0)))

        quality = (
            (1.0 - self.config.diversity_weight) * perplexity_score
            + self.config.diversity_weight * diversity_score
        ) * length_score

        return True, max(0.0, min(1.0, quality))

    def score(self, document: ProcessedDocument) -> float:
        text = document.text
        _, quality = self._check_quality(text)
        return quality

    def process(self, document: ProcessedDocument) -> ProcessedDocument | None:
        if not self.config.enabled:
            document.quality_score = 1.0
            return document
        passes, quality = self._check_quality(document.text)
        if not passes:
            return None
        document.quality_score = quality
        if document.quality_score < self.config.min_quality_score:
            return None
        return document


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------


class LanguageDetector:
    def __init__(self, config: LanguageConfig) -> None:
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

    def process(self, document: ProcessedDocument) -> ProcessedDocument | None:
        if not self.config.enabled:
            document.language = self.config.default_language
            document.language_confidence = 1.0
            return document
        lang, confidence = self.detect(document.text)
        document.language = lang
        document.language_confidence = confidence
        if confidence < self.config.confidence_threshold:
            document.language = self.config.default_language
        if document.language not in self.config.allowed_languages:
            return None
        return document


# ---------------------------------------------------------------------------
# PII removal (enhanced)
# ---------------------------------------------------------------------------


class PiiRemover:
    _EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    _PHONE_RE = re.compile(r"(?:(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})")
    _IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
    _SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
    _CREDIT_CARD_RE = re.compile(
        r"\b(?:\d{4}[-\s]?){3}\d{4}\b|\b\d{13,16}\b"
    )
    _IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{1,30}\b")
    _MEDICAL_RE = re.compile(
        r"\b(?:patient|diagnosis|medical|prescription|treatment)\s+(?:id|number|code|record)[:\s]*\w+\b",
        re.IGNORECASE,
    )

    def __init__(self, config: PiiConfig) -> None:
        self.config = config
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
        if self.config.strip_medical:
            text = self._MEDICAL_RE.sub(self.config.replacement, text)
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


# ---------------------------------------------------------------------------
# Domain-specific cleaners
# ---------------------------------------------------------------------------


class CodeCleaner:
    _FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
    _EXCESSIVE_BLANKS = re.compile(r"\n{4,}")

    def process(self, document: ProcessedDocument) -> ProcessedDocument:
        text = self._FENCE_RE.sub("", document.text)
        text = self._EXCESSIVE_BLANKS.sub("\n\n\n", text)
        document.text = text.strip()
        return document


class MathCleaner:
    _BROKEN_LATEX_RE = re.compile(r"\$[^$]*\$|\$\$[^$]*\$\$", re.DOTALL)

    def _balanced_equations(self, text: str) -> str:
        def keep_equation(match: re.Match) -> str:
            eq = match.group(0)
            if eq.count("{") == eq.count("}") and eq.count("$") == 2:
                return eq
            return ""

        return self._BROKEN_LATEX_RE.sub(keep_equation, text)

    def process(self, document: ProcessedDocument) -> ProcessedDocument:
        text = self._balanced_equations(document.text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        document.text = text.strip()
        return document


class WikipediaCleaner:
    _WIKI_MARKUP = re.compile(r"\[\[|\]\]|\{\{|\}\}|<ref.*?</ref>", re.DOTALL)
    _INFOBOX = re.compile(r"\|[^=]*=[^|\n]*", re.DOTALL)
    _REFERENCES = re.compile(r"==\s*References\s*==.*", re.DOTALL | re.IGNORECASE)
    _CATEGORIES = re.compile(r"\[\[Category:[^\]]*\]\]", re.IGNORECASE)

    def process(self, document: ProcessedDocument) -> ProcessedDocument:
        text = document.text
        text = self._WIKI_MARKUP.sub("", text)
        text = self._INFOBOX.sub("", text)
        text = self._CATEGORIES.sub("", text)
        text = self._REFERENCES.sub("", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        document.text = text.strip()
        return document


class BooksCleaner:
    _CHAPTER_HEADER = re.compile(
        r"^(chapter\s+\d+|part\s+\d+|[ivxlcdm]+\b.*)$",
        re.IGNORECASE | re.MULTILINE,
    )
    _BOILERPLATE = re.compile(
        r"(published\s+by|all\s+rights\s+reserved|isbn\s*[\d-]+|copyright\s*[\d]{4})",
        re.IGNORECASE,
    )

    def process(self, document: ProcessedDocument) -> ProcessedDocument:
        text = document.text
        text = self._CHAPTER_HEADER.sub("", text)
        text = self._BOILERPLATE.sub("", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        document.text = text.strip()
        return document


class AcademicCleaner:
    _ABSTRACT = re.compile(r"Abstract\s*[-–—]?\s*(.*?)(?=\n\s*\n|\Z)", re.DOTALL | re.IGNORECASE)
    _REFERENCES = re.compile(r"References\s*\n.*", re.DOTALL | re.IGNORECASE)
    _BIBTEX = re.compile(r"@\w+\s*\{[^}]*\}", re.DOTALL)

    def process(self, document: ProcessedDocument) -> ProcessedDocument:
        text = document.text
        text = self._REFERENCES.sub("", text)
        text = self._BIBTEX.sub("", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        document.text = text.strip()
        return document


class ConversationCleaner:
    _EXCESSIVE_TURNS = re.compile(r"(User:|Assistant:)\s*\1", re.IGNORECASE)
    _SYSTEM_PROMPTS = re.compile(
        r"(You are a|You are an|As an AI|As a language model|I'm an AI|I'm a large language model)",
        re.IGNORECASE,
    )

    def process(self, document: ProcessedDocument) -> ProcessedDocument:
        text = document.text
        text = self._SYSTEM_PROMPTS.sub("", text)
        text = self._EXCESSIVE_TURNS.sub(r"\1", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        document.text = text.strip()
        return document


class QACleaner:
    _BOILERPLATE = re.compile(
        r"(This question|The following|Consider the|Based on the|According to)",
        re.IGNORECASE,
    )

    def process(self, document: ProcessedDocument) -> ProcessedDocument:
        text = document.text
        text = self._BOILERPLATE.sub("", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        document.text = text.strip()
        return document


class OcrCleaner:
    _OCR_ERRORS = re.compile(r"\b[Il1]{3,}\b|\b[O0]{3,}\b|[\|]")
    _LINE_BREAKS = re.compile(r"\n\s*\n")

    def process(self, document: ProcessedDocument) -> ProcessedDocument:
        text = document.text
        text = self._OCR_ERRORS.sub(" ", text)
        text = self._LINE_BREAKS.sub("\n\n", text)
        document.text = text.strip()
        return document


class ImageCaptionCleaner:
    def process(self, document: ProcessedDocument) -> ProcessedDocument:
        text = document.text
        text = re.sub(r"\b(fig|figure|img|image|photo|picture)\s*\.?\s*\d*\b", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\n{3,}", "\n\n", text)
        document.text = text.strip()
        return document


# ---------------------------------------------------------------------------
# Domain balancing
# ---------------------------------------------------------------------------


class DomainBalancer:
    DOMAINS = [
        "web",
        "wiki",
        "books",
        "academic",
        "code",
        "math",
        "qa",
        "conversations",
        "ocr",
        "image_caption",
        "multilingual",
    ]

    def __init__(self, target_ratios: dict[str, float] | None = None) -> None:
        if target_ratios is None:
            target_ratios = {d: 1.0 / len(self.DOMAINS) for d in self.DOMAINS}
        self.target_ratios = target_ratios
        self.buffers: dict[str, list[ProcessedDocument]] = {d: [] for d in self.DOMAINS}
        self.total_seen = 0

    def add(self, document: ProcessedDocument) -> None:
        domain = document.domain or "general"
        if domain not in self.buffers:
            domain = "general" if "general" in self.buffers else list(self.buffers.keys())[0]
        self.buffers[domain].append(document)
        self.total_seen += 1

    def sample(self) -> Iterator[ProcessedDocument]:
        if self.total_seen == 0:
            return
        for domain, docs in self.buffers.items():
            target = self.target_ratios.get(domain, 0.0)
            desired = int(self.total_seen * target)
            if len(docs) > desired:
                random.shuffle(docs)
                docs = docs[:desired]
            yield from docs


# ---------------------------------------------------------------------------
# Dataset versioning
# ---------------------------------------------------------------------------


class DatasetVersionManager:
    def __init__(self, versions_file: str = "data/dataset_versions.json") -> None:
        self.versions_file = Path(versions_file)
        self.versions_file.parent.mkdir(parents=True, exist_ok=True)
        self._versions: list[dict[str, Any]] = self._load()

    def _load(self) -> list[dict[str, Any]]:
        if self.versions_file.exists():
            try:
                with self.versions_file.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as exc:
                logger.warning("Failed to load versions: %s", exc)
        return []

    def _save(self) -> None:
        try:
            with self.versions_file.open("w", encoding="utf-8") as f:
                json.dump(self._versions, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            logger.error("Failed to save versions: %s", exc)

    def create_version(
        self,
        source: str,
        documents_count: int,
        tokens_count: int,
        config: DatasetEngineeringConfig,
    ) -> DatasetVersion:
        version_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()
        config_dict = {
            "dedup": config.dedup.__dict__,
            "toxicity": config.toxicity.__dict__,
            "quality": config.quality.__dict__,
            "language": config.language.__dict__,
            "pii": config.pii.__dict__,
        }
        checksum = hashlib.sha256(
            json.dumps(config_dict, sort_keys=True).encode("utf-8")
        ).hexdigest()[:16]
        version = DatasetVersion(
            version=version_id,
            created_at=now,
            source=source,
            documents_count=documents_count,
            tokens_count=tokens_count,
            config_snapshot=config_dict,
            checksum=checksum,
        )
        self._versions.append(version.to_dict())
        self._save()
        logger.info("Created dataset version %s for %s", version_id, source)
        return version

    def get_versions(self) -> list[dict[str, Any]]:
        return list(self._versions)

    def get_latest(self) -> dict[str, Any] | None:
        return self._versions[-1] if self._versions else None


# ---------------------------------------------------------------------------
# Report generator
# ---------------------------------------------------------------------------


class DatasetReportGenerator:
    def __init__(self, stats: DatasetStats, config: DatasetEngineeringConfig) -> None:
        self.stats = stats
        self.config = config

    def _ascii_bar(self, label: str, value: int, total: int, width: int = 30) -> str:
        if total == 0:
            pct = 0.0
            bar = ""
        else:
            pct = value / total
            bar = "#" * int(pct * width)
        return f"{label:<20} |{bar:<{width}} | {value} ({pct:.1%})"

    def generate(self) -> str:
        stats = self.stats
        lines: list[str] = []
        lines.append("# Dataset Engineering Report")
        lines.append("")
        lines.append(f"*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        lines.append(f"*Dataset version: {stats.dataset_version}*")
        lines.append("")
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Total Documents:** {stats.total_documents:,}")
        lines.append(f"- **Kept Documents:** {stats.kept_documents:,}")
        lines.append(f"- **Removed Exact Duplicates:** {stats.removed_exact_duplicates:,}")
        lines.append(f"- **Removed Near Duplicates:** {stats.removed_near_duplicates:,}")
        lines.append(f"- **Removed Bloom Filter:** {stats.removed_bloom:,}")
        lines.append(f"- **Removed Toxicity:** {stats.removed_toxicity:,}")
        lines.append(f"- **Removed PII:** {stats.removed_pii:,}")
        lines.append(f"- **Removed Quality:** {stats.removed_quality:,}")
        lines.append(f"- **Removed Language:** {stats.removed_language:,}")
        lines.append(f"- **Processing Time:** {stats.processing_time_seconds:.2f}s")
        lines.append(f"- **Total Tokens:** {stats.token_stats.get('total_tokens', 0):,}")
        lines.append(f"- **Avg Tokens/Doc:** {stats.token_stats.get('avg_tokens_per_doc', 0):.1f}")
        lines.append("")
        lines.append("## Domain Distribution")
        lines.append("")
        lines.append("```")
        total = sum(stats.domains.values()) if stats.domains else 0
        for label, value in sorted(stats.domains.items(), key=lambda x: x[1], reverse=True):
            lines.append(self._ascii_bar(label, value, total))
        lines.append("```")
        lines.append("")
        lines.append("## Language Distribution")
        lines.append("")
        lines.append("| Language | Count | Percentage |")
        lines.append("|----------|-------|------------|")
        lang_total = sum(stats.languages.values()) if stats.languages else 0
        for label, value in sorted(stats.languages.items(), key=lambda x: x[1], reverse=True)[:20]:
            pct = (value / lang_total * 100) if lang_total > 0 else 0.0
            lines.append(f"| {label} | {value:,} | {pct:.2f}% |")
        lines.append("")
        lines.append("## Token Statistics")
        lines.append("")
        lines.append(f"- **Total Tokens:** {stats.token_stats.get('total_tokens', 0):,}")
        lines.append(f"- **Avg Tokens/Doc:** {stats.token_stats.get('avg_tokens_per_doc', 0):.1f}")
        lines.append(f"- **Min Tokens/Doc:** {stats.token_stats.get('min_tokens_per_doc', 0):.1f}")
        lines.append(f"- **Max Tokens/Doc:** {stats.token_stats.get('max_tokens_per_doc', 0):.1f}")
        lines.append("")
        lines.append("## Retention Rate")
        lines.append("")
        if stats.total_documents > 0:
            retention = (stats.kept_documents / stats.total_documents) * 100
            lines.append(f"- **Overall Retention:** {retention:.2f}%")
        lines.append("")
        return "\n".join(lines)

    def save(self, path: str | None = None) -> str:
        output = path or f"reports/dataset_report_{self.stats.dataset_version}.md"
        try:
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            with open(output, "w", encoding="utf-8") as f:
                f.write(self.generate())
            logger.info("Report saved to %s", output)
            return output
        except OSError as exc:
            logger.error("Failed to save report: %s", exc)
            raise


# ---------------------------------------------------------------------------
# Format I/O
# ---------------------------------------------------------------------------


class DatasetIO:
    @staticmethod
    def _read_txt(path: Path, chunk_size: int) -> Iterator[str]:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk

    @staticmethod
    def _read_jsonl(path: Path, chunk_size: int) -> Iterator[dict[str, Any]]:
        if _HAS_IJSON:
            with path.open("rb") as f:
                yield from ijson.items(f, "item")
        else:
            with path.open("r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue

    @staticmethod
    def _read_parquet(path: Path) -> Iterator[dict[str, Any]]:
        if not _HAS_PYARROW:
            raise ImportError("pyarrow is required for parquet support")
        table = pq.read_table(str(path))
        df = table.to_pandas()
        for _, row in df.iterrows():
            yield row.to_dict()

    @staticmethod
    def iter_documents(
        path: str | Path,
        text_field: str = "text",
        source_field: str = "source",
        domain_field: str = "domain",
        chunk_size: int = 10_000,
    ) -> Iterator[ProcessedDocument]:
        path = Path(path)
        suffix = path.suffix.lower()
        if suffix == ".txt":
            for chunk in DatasetIO._read_txt(path, chunk_size):
                yield ProcessedDocument(text=chunk)
        elif suffix == ".jsonl":
            for item in DatasetIO._read_jsonl(path, chunk_size):
                if not isinstance(item, dict):
                    continue
                text = item.get(text_field, "")
                if not text:
                    continue
                yield ProcessedDocument(
                    text=str(text),
                    source=str(item.get(source_field, path.name)),
                    domain=str(item.get(domain_field, "general")),
                )
        elif suffix == ".parquet":
            for item in DatasetIO._read_parquet(path):
                text = item.get(text_field, "")
                if not text:
                    continue
                yield ProcessedDocument(
                    text=str(text),
                    source=str(item.get(source_field, path.name)),
                    domain=str(item.get(domain_field, "general")),
                )
        else:
            raise ValueError(f"Unsupported format: {suffix}")

    @staticmethod
    def write_jsonl(
        documents: Iterable[ProcessedDocument],
        path: str | Path,
    ) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            for doc in documents:
                record = {
                    "text": doc.text,
                    "source": doc.source,
                    "domain": doc.domain,
                    "quality_score": doc.quality_score,
                    "language": doc.language,
                    "language_confidence": doc.language_confidence,
                    "pii_removed": doc.pii_removed,
                    "dedup_hash": doc.dedup_hash,
                    "simhash": doc.simhash,
                    "token_count": doc.token_count,
                    "metadata": doc.metadata,
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Dataset ingestion pipelines
# ---------------------------------------------------------------------------


class BaseIngestionPipeline:
    DOMAIN: str = "general"
    SOURCE: str = "unknown"

    def __init__(self, config: DatasetEngineeringConfig) -> None:
        self.config = config
        self.output_dir = Path(config.ingestion.output_dir) / self.DOMAIN
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir = Path(config.ingestion.raw_dir) / self.DOMAIN
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir = Path(config.ingestion.cache_dir) / self.DOMAIN
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch(self) -> Iterator[dict[str, Any]]:
        raise NotImplementedError

    def process_documents(
        self,
        documents: Iterator[ProcessedDocument],
        pipeline: DatasetEngineeringPipeline,
    ) -> Iterator[ProcessedDocument]:
        for doc in documents:
            doc.domain = doc.domain or self.DOMAIN
            doc.source = doc.source or self.SOURCE
            doc.token_count = TextUtils.count_tokens(doc.text)
            processed = pipeline.process_document(doc)
            if processed is not None:
                yield processed

    def run(self, pipeline: DatasetEngineeringPipeline) -> DatasetStats:
        stats = DatasetStats()
        start = time.time()
        output_file = self.output_dir / f"{self.DOMAIN}_{self.config.ingestion.version}.jsonl"
        documents: list[ProcessedDocument] = []
        chunk_size = self.config.ingestion.streaming_chunk_size
        for doc in self.process_documents(self.fetch(), pipeline):
            documents.append(doc)
            stats.total_documents += 1
            if len(documents) >= chunk_size:
                DatasetIO.write_jsonl(documents, output_file)
                stats.kept_documents += len(documents)
                documents = []
        if documents:
            DatasetIO.write_jsonl(documents, output_file)
            stats.kept_documents += len(documents)
        stats.processing_time_seconds = time.time() - start
        stats.dataset_version = self.config.ingestion.version
        logger.info(
            "%s pipeline: %d docs in %.2fs (%.1f docs/s)",
            self.DOMAIN,
            stats.total_documents,
            stats.processing_time_seconds,
            stats.total_documents / max(stats.processing_time_seconds, 0.001),
        )
        return stats


class WebCrawlPipeline(BaseIngestionPipeline):
    DOMAIN = "web"
    SOURCE = "common_crawl"

    def fetch(self) -> Iterator[dict[str, Any]]:
        if _HAS_DATASETS:
            try:
                ds = load_dataset(
                    "allenai/c4",
                    "en",
                    split="train",
                    streaming=True,
                    trust_remote_code=True,
                )
                for example in ds:
                    yield {
                        "text": example.get("text", ""),
                        "source": "c4",
                        "domain": "web",
                    }
            except Exception as exc:
                logger.warning("C4 streaming failed: %s", exc)
        if _HAS_DATASETS:
            try:
                ds = load_dataset(
                    "HuggingFaceFW/fineweb",
                    "sample-10BT",
                    split="train",
                    streaming=True,
                    trust_remote_code=True,
                )
                for example in ds:
                    yield {
                        "text": example.get("text", ""),
                        "source": "fineweb",
                        "domain": "web",
                    }
            except Exception as exc:
                logger.warning("FineWeb streaming failed: %s", exc)
        yield from []


class WikipediaPipeline(BaseIngestionPipeline):
    DOMAIN = "wiki"
    SOURCE = "wikipedia"

    LANGUAGES = [
        "en",
        "es",
        "fr",
        "de",
        "it",
        "pt",
        "ru",
        "zh",
        "ja",
        "ko",
        "ar",
        "hi",
        "bn",
        "pa",
        "jv",
        "tr",
        "vi",
        "th",
        "id",
        "ms",
        "cs",
        "pl",
        "nl",
        "sv",
        "da",
        "no",
        "fi",
        "el",
        "he",
        "ro",
        "hu",
        "uk",
        "bg",
        "hr",
        "sr",
        "sk",
        "sl",
        "lt",
        "lv",
        "et",
        "tl",
        "sw",
        "zu",
        "af",
        "ka",
        "hy",
        "az",
        "kk",
        "uz",
        "mn",
        "my",
        "km",
        "lo",
        "ne",
        "si",
        "ta",
        "te",
        "kn",
        "ml",
        "mr",
        "gu",
        "ur",
        "fa",
        "ps",
        "ku",
        "am",
        "so",
        "yo",
        "ig",
        "ha",
        "eu",
        "gl",
        "ca",
        "cy",
        "is",
        "ga",
        "mt",
        "sq",
        "mk",
        "be",
        "ky",
        "tg",
        "tk",
        "tt",
        "ba",
        "cv",
        "ce",
        "os",
        "sah",
        "mhr",
        "myv",
        "udm",
        "mdf",
        "koi",
        "kum",
        "nog",
        "kbd",
        "ady",
        "ab",
        "av",
        "le",
        "lbe",
        "tab",
        "tly",
        "dv",
        "ff",
        "bm",
        "tn",
        "ts",
        "ve",
        "nr",
        "ss",
        "st",
        "xh",
        "sn",
        "kr",
        "tw",
        "ee",
        "fon",
        "ln",
        "kg",
        "lg",
        "lu",
        "rn",
        "ik",
        "iu",
        "oj",
        "cr",
        "nv",
        "ht",
        "ay",
        "qu",
        "gn",
        "cbk",
        "ia",
        "eo",
        "vo",
        "jbo",
        "nov",
        "tok",
        "ido",
        "ie",
        "alt",
        "bxr",
        "ruq",
        "rue",
        "be-x-old",
        "mwl",
        "dsb",
        "hsb",
        "gsw",
        "pdc",
        "gcr",
        "frp",
        "oc",
        "co",
        "sc",
        "rm",
        "fur",
        "lij",
        "nap",
        "scn",
        "vec",
        "lad",
        "rup",
        "la",
        "grc",
        "enm",
        "ang",
        "non",
        "goh",
        "osx",
        "fro",
        "wa",
        "pms",
        "ast",
        "ext",
        "roa-opt",
        "roa-tara",
    ]

    def fetch(self) -> Iterator[dict[str, Any]]:
        if _HAS_DATASETS:
            for lang in self.LANGUAGES:
                try:
                    ds = load_dataset(
                        "wikimedia/wikipedia",
                        f"20231101.{lang}",
                        split="train",
                        streaming=True,
                        trust_remote_code=True,
                    )
                    for example in ds:
                        yield {
                            "text": example.get("text", ""),
                            "source": f"wikipedia_{lang}",
                            "domain": "wiki",
                            "language": lang,
                        }
                except Exception as exc:
                    logger.debug("Wikipedia %s streaming failed: %s", lang, exc)
        yield from []


class BooksPipeline(BaseIngestionPipeline):
    DOMAIN = "books"
    SOURCE = "gutenberg"

    def fetch(self) -> Iterator[dict[str, Any]]:
        if _HAS_DATASETS:
            try:
                ds = load_dataset(
                    "sedthh/gutenberg_english",
                    "gutenberg_english",
                    split="train",
                    streaming=True,
                    trust_remote_code=True,
                )
                for example in ds:
                    yield {
                        "text": example.get("text", ""),
                        "source": "gutenberg",
                        "domain": "books",
                    }
            except Exception as exc:
                logger.warning("Gutenberg English failed: %s", exc)
            try:
                ds = load_dataset(
                    "sedthh/gutenberg_multilang",
                    "gutenberg_multilang",
                    split="train",
                    streaming=True,
                    trust_remote_code=True,
                )
                for example in ds:
                    yield {
                        "text": example.get("text", ""),
                        "source": "gutenberg_multilang",
                        "domain": "books",
                        "language": example.get("language", "en"),
                    }
            except Exception as exc:
                logger.warning("Gutenberg Multilang failed: %s", exc)
        yield from []


class AcademicPipeline(BaseIngestionPipeline):
    DOMAIN = "academic"
    SOURCE = "arxiv"

    def fetch(self) -> Iterator[dict[str, Any]]:
        if _HAS_DATASETS:
            try:
                ds = load_dataset(
                    "arxiv_dataset",
                    "arxiv_dataset",
                    split="train",
                    streaming=True,
                    trust_remote_code=True,
                )
                for example in ds:
                    yield {
                        "text": example.get("abstract", "") + "\n" + example.get("title", ""),
                        "source": "arxiv",
                        "domain": "academic",
                        "metadata": {
                            "arxiv_id": example.get("id", ""),
                            "categories": example.get("categories", ""),
                        },
                    }
            except Exception as exc:
                logger.warning("ArXiv streaming failed: %s", exc)
            try:
                ds = load_dataset(
                    "ccdv/pubmed-summarization",
                    split="train",
                    streaming=True,
                    trust_remote_code=True,
                )
                for example in ds:
                    yield {
                        "text": example.get("article", ""),
                        "source": "pubmed",
                        "domain": "academic",
                    }
            except Exception as exc:
                logger.warning("PubMed streaming failed: %s", exc)
        yield from []


class CodePipeline(BaseIngestionPipeline):
    DOMAIN = "code"
    SOURCE = "github"

    def fetch(self) -> Iterator[dict[str, Any]]:
        if _HAS_DATASETS:
            try:
                ds = load_dataset(
                    "codeparrot/github-code",
                    "python",
                    split="train",
                    streaming=True,
                    trust_remote_code=True,
                )
                for example in ds:
                    yield {
                        "text": example.get("code", ""),
                        "source": "github",
                        "domain": "code",
                    }
            except Exception as exc:
                logger.warning("GitHub Code streaming failed: %s", exc)
            try:
                ds = load_dataset(
                    "HuggingFaceH4/stack-exchange-preferences",
                    split="train",
                    streaming=True,
                    trust_remote_code=True,
                )
                for example in ds:
                    yield {
                        "text": example.get("question", "") + "\n" + example.get("answer", ""),
                        "source": "stackexchange",
                        "domain": "code",
                    }
            except Exception as exc:
                logger.warning("Stack Exchange streaming failed: %s", exc)
            try:
                ds = load_dataset(
                    "bigcode/the-stack",
                    "python",
                    split="train",
                    streaming=True,
                    trust_remote_code=True,
                )
                for example in ds:
                    yield {
                        "text": example.get("content", ""),
                        "source": "the_stack",
                        "domain": "code",
                    }
            except Exception as exc:
                logger.warning("The Stack streaming failed: %s", exc)
        yield from []


class MathPipeline(BaseIngestionPipeline):
    DOMAIN = "math"
    SOURCE = "openwebmath"

    def fetch(self) -> Iterator[dict[str, Any]]:
        if _HAS_DATASETS:
            try:
                ds = load_dataset(
                    "open-web-math/open-web-math",
                    split="train",
                    streaming=True,
                    trust_remote_code=True,
                )
                for example in ds:
                    yield {
                        "text": example.get("text", ""),
                        "source": "openwebmath",
                        "domain": "math",
                    }
            except Exception as exc:
                logger.warning("OpenWebMath streaming failed: %s", exc)
            try:
                ds = load_dataset(
                    "EleutherAI/hendrycks_math",
                    "algebra",
                    split="train",
                    streaming=True,
                    trust_remote_code=True,
                )
                for example in ds:
                    yield {
                        "text": example.get("problem", "") + "\n" + example.get("solution", ""),
                        "source": "hendrycks_math",
                        "domain": "math",
                    }
            except Exception as exc:
                logger.warning("Hendrycks Math streaming failed: %s", exc)
        yield from []


class QAPipeline(BaseIngestionPipeline):
    DOMAIN = "qa"
    SOURCE = "natural_questions"

    def fetch(self) -> Iterator[dict[str, Any]]:
        if _HAS_DATASETS:
            try:
                ds = load_dataset(
                    "natural_questions",
                    split="train",
                    streaming=True,
                    trust_remote_code=True,
                )
                for example in ds:
                    yield {
                        "text": example.get("question", {}).get("text", "")
                        + "\n"
                        + example.get("answer", {}).get("text", ""),
                        "source": "natural_questions",
                        "domain": "qa",
                    }
            except Exception as exc:
                logger.warning("Natural Questions streaming failed: %s", exc)
            try:
                ds = load_dataset(
                    "trivia_qa",
                    "rc",
                    split="train",
                    streaming=True,
                    trust_remote_code=True,
                )
                for example in ds:
                    yield {
                        "text": example.get("question", "") + "\n" + example.get("answer", {}).get("value", ""),
                        "source": "triviaqa",
                        "domain": "qa",
                    }
            except Exception as exc:
                logger.warning("TriviaQA streaming failed: %s", exc)
            try:
                ds = load_dataset(
                    "deepmind/code_contests",
                    split="train",
                    streaming=True,
                    trust_remote_code=True,
                )
                for example in ds:
                    yield {
                        "text": example.get("description", ""),
                        "source": "code_contests",
                        "domain": "qa",
                    }
            except Exception as exc:
                logger.warning("Code Contests streaming failed: %s", exc)
        yield from []


class ConversationPipeline(BaseIngestionPipeline):
    DOMAIN = "conversations"
    SOURCE = "sharegpt"

    def fetch(self) -> Iterator[dict[str, Any]]:
        if _HAS_DATASETS:
            try:
                ds = load_dataset(
                    "AlekseyKorshuk/saiga-tokenized",
                    split="train",
                    streaming=True,
                    trust_remote_code=True,
                )
                for example in ds:
                    yield {
                        "text": example.get("text", ""),
                        "source": "saiga",
                        "domain": "conversations",
                    }
            except Exception as exc:
                logger.warning("Saiga streaming failed: %s", exc)
            try:
                ds = load_dataset(
                    "Open-Orca/OpenOrca",
                    split="train",
                    streaming=True,
                    trust_remote_code=True,
                )
                for example in ds:
                    yield {
                        "text": example.get("system_prompt", "")
                        + "\nUser: "
                        + example.get("question", "")
                        + "\nAssistant: "
                        + example.get("response", ""),
                        "source": "openorca",
                        "domain": "conversations",
                    }
            except Exception as exc:
                logger.warning("OpenOrca streaming failed: %s", exc)
            try:
                ds = load_dataset(
                    "HuggingFaceH4/ultrachat_200k",
                    split="train_sft",
                    streaming=True,
                    trust_remote_code=True,
                )
                for example in ds:
                    yield {
                        "text": example.get("prompt", "") + example.get("chosen", ""),
                        "source": "ultrachat",
                        "domain": "conversations",
                    }
            except Exception as exc:
                logger.warning("UltraChat streaming failed: %s", exc)
        yield from []


class OcrPipeline(BaseIngestionPipeline):
    DOMAIN = "ocr"
    SOURCE = "scanned_documents"

    def fetch(self) -> Iterator[dict[str, Any]]:
        if _HAS_DATASETS:
            try:
                ds = load_dataset(
                    "openai/grade-school-math",
                    split="train",
                    streaming=True,
                    trust_remote_code=True,
                )
                for example in ds:
                    yield {
                        "text": example.get("problem", "") + "\n" + example.get("solution", ""),
                        "source": "grade_school_math",
                        "domain": "ocr",
                    }
            except Exception as exc:
                logger.warning("Grade School Math streaming failed: %s", exc)
        yield from []


class ImageCaptionPipeline(BaseIngestionPipeline):
    DOMAIN = "image_caption"
    SOURCE = "image_caption"

    def fetch(self) -> Iterator[dict[str, Any]]:
        if _HAS_DATASETS:
            try:
                ds = load_dataset(
                    "yomnah-bitmoji/bitmoji",
                    split="train",
                    streaming=True,
                    trust_remote_code=True,
                )
                for example in ds:
                    caption = example.get("text", example.get("caption", ""))
                    if caption:
                        yield {
                            "text": caption,
                            "source": "bitmoji",
                            "domain": "image_caption",
                            "metadata": {"image_id": example.get("image_id", "")},
                        }
            except Exception as exc:
                logger.debug("Bitmoji dataset failed: %s", exc)
            try:
                ds = load_dataset(
                    "HuggingFaceM4/COCO",
                    split="train",
                    streaming=True,
                    trust_remote_code=True,
                )
                for example in ds:
                    caption = example.get("sentences", {}).get("raw", [""])[0] if example.get("sentences") else ""
                    if caption:
                        yield {
                            "text": caption,
                            "source": "coco",
                            "domain": "image_caption",
                            "metadata": {"image_id": example.get("image_id", "")},
                        }
            except Exception as exc:
                logger.debug("COCO dataset failed: %s", exc)
        yield from []


class MultilingualPipeline(BaseIngestionPipeline):
    DOMAIN = "multilingual"
    SOURCE = "fineweb_multilingual"

    def fetch(self) -> Iterator[dict[str, Any]]:
        if _HAS_DATASETS:
            try:
                ds = load_dataset(
                    "HuggingFaceFW/fineweb",
                    "multilingual",
                    split="train",
                    streaming=True,
                    trust_remote_code=True,
                )
                for example in ds:
                    yield {
                        "text": example.get("text", ""),
                        "source": "fineweb_multilingual",
                        "domain": "multilingual",
                    }
            except Exception as exc:
                logger.warning("FineWeb multilingual failed: %s", exc)
            try:
                ds = load_dataset(
                    "ccdv/annotated-wikipedia",
                    split="train",
                    streaming=True,
                    trust_remote_code=True,
                )
                for example in ds:
                    yield {
                        "text": example.get("text", ""),
                        "source": "annotated_wikipedia",
                        "domain": "multilingual",
                    }
            except Exception as exc:
                logger.warning("Annotated Wikipedia failed: %s", exc)
        yield from []


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


class DatasetEngineeringPipeline:
    def __init__(self, config: DatasetEngineeringConfig | None = None) -> None:
        self.config = config or DatasetEngineeringConfig()
        random.seed(self.config.seed)
        self.dedup = Deduplicator(self.config.dedup)
        self.toxicity = ToxicityFilter(self.config.toxicity)
        self.quality = QualityScorer(self.config.quality)
        self.language = LanguageDetector(self.config.language)
        self.pii = PiiRemover(self.config.pii)
        self.code_cleaner = CodeCleaner()
        self.math_cleaner = MathCleaner()
        self.wiki_cleaner = WikipediaCleaner()
        self.books_cleaner = BooksCleaner()
        self.academic_cleaner = AcademicCleaner()
        self.conversation_cleaner = ConversationCleaner()
        self.qa_cleaner = QACleaner()
        self.ocr_cleaner = OcrCleaner()
        self.image_caption_cleaner = ImageCaptionCleaner()
        self.balancer = DomainBalancer(self.config.domain_balance.target_ratios)
        self.stats = DatasetStats()
        self.version_manager = DatasetVersionManager()

    def _select_cleaner(self, domain: str) -> Callable[[ProcessedDocument], ProcessedDocument]:
        domain = domain.lower()
        cleaners = {
            "math": self.math_cleaner.process,
            "wiki": self.wiki_cleaner.process,
            "books": self.books_cleaner.process,
            "academic": self.academic_cleaner.process,
            "code": self.code_cleaner.process,
            "conversations": self.conversation_cleaner.process,
            "qa": self.qa_cleaner.process,
            "ocr": self.ocr_cleaner.process,
            "image_caption": self.image_caption_cleaner.process,
        }
        return cleaners.get(domain, lambda d: d)

    def process_document(self, document: ProcessedDocument) -> ProcessedDocument | None:
        document.domain = document.domain or self.config.domain
        document.source = document.source or self.config.source

        document = self.dedup.process(document)
        if document is None:
            self.stats.removed_exact_duplicates += 1
            return None

        document = self.toxicity.process(document)
        if document is None:
            self.stats.removed_toxicity += 1
            return None

        document = self.language.process(document)
        if document is None:
            self.stats.removed_language += 1
            return None

        cleaner = self._select_cleaner(document.domain)
        document = cleaner(document)

        document = self.pii.process(document)

        document = self.quality.process(document)
        if document is None:
            self.stats.removed_quality += 1
            return None

        document.token_count = TextUtils.count_tokens(document.text)

        self.stats.domains[document.domain] = self.stats.domains.get(document.domain, 0) + 1
        self.stats.languages[document.language] += 1
        self.stats.kept_documents += 1
        return document

    def process_stream(
        self,
        input_path: str | Path,
        output_path: str | Path,
        text_field: str = "text",
        source_field: str = "source",
        domain_field: str = "domain",
    ) -> DatasetStats:
        self.stats = DatasetStats()
        documents: list[ProcessedDocument] = []

        for document in DatasetIO.iter_documents(
            input_path,
            text_field=text_field,
            source_field=source_field,
            domain_field=domain_field,
            chunk_size=self.config.ingestion.streaming_chunk_size,
        ):
            self.stats.total_documents += 1
            processed = self.process_document(document)
            if processed is not None:
                documents.append(processed)

            if len(documents) >= self.config.ingestion.streaming_chunk_size:
                balanced = self.balancer.sample()
                DatasetIO.write_jsonl(balanced, output_path)
                documents = []

        if documents:
            balanced = self.balancer.sample()
            DatasetIO.write_jsonl(balanced, output_path)

        total_tokens = sum(d.token_count for d in self.balancer.buffers.values() for d in d)
        avg_tokens = total_tokens / max(self.stats.kept_documents, 1)
        self.stats.token_stats = {
            "total_tokens": total_tokens,
            "avg_tokens_per_doc": avg_tokens,
            "min_tokens_per_doc": min(
                (d.token_count for docs in self.balancer.buffers.values() for d in docs),
                default=0,
            ),
            "max_tokens_per_doc": max(
                (d.token_count for docs in self.balancer.buffers.values() for d in docs),
                default=0,
            ),
        }
        return self.stats

    def run_ingestion(
        self,
        pipeline: BaseIngestionPipeline,
        version_manager: DatasetVersionManager | None = None,
    ) -> DatasetStats:
        stats = pipeline.run(self)
        version_manager = version_manager or self.version_manager
        total_tokens = stats.token_stats.get("total_tokens", 0)
        version_manager.create_version(
            source=pipeline.SOURCE,
            documents_count=stats.kept_documents,
            tokens_count=total_tokens,
            config=self.config,
        )
        report_path = self.output_dir / f"report_{self.config.ingestion.version}.md"
        report = DatasetReportGenerator(stats, self.config)
        report.save(str(report_path))
        logger.info("Report saved to %s", report_path)
        return stats

    def run_all(self) -> dict[str, DatasetStats]:
        pipelines = [
            WebCrawlPipeline(self.config),
            WikipediaPipeline(self.config),
            BooksPipeline(self.config),
            AcademicPipeline(self.config),
            CodePipeline(self.config),
            MathPipeline(self.config),
            QAPipeline(self.config),
            ConversationPipeline(self.config),
            OcrPipeline(self.config),
            ImageCaptionPipeline(self.config),
            MultilingualPipeline(self.config),
        ]
        results: dict[str, DatasetStats] = {}
        for pipeline in pipelines:
            logger.info("Running pipeline: %s", pipeline.DOMAIN)
            try:
                stats = self.run_ingestion(pipeline)
                results[pipeline.DOMAIN] = stats
            except Exception as exc:
                logger.error("Pipeline %s failed: %s", pipeline.DOMAIN, exc)
                results[pipeline.DOMAIN] = DatasetStats()
        return results


# ---------------------------------------------------------------------------
# Convenience API
# ---------------------------------------------------------------------------


def run_dataset_engineering(
    input_path: str | Path,
    output_path: str | Path,
    config: DatasetEngineeringConfig | None = None,
    text_field: str = "text",
    source_field: str = "source",
    domain_field: str = "domain",
) -> DatasetStats:
    pipeline = DatasetEngineeringPipeline(config)
    return pipeline.process_stream(
        input_path=input_path,
        output_path=output_path,
        text_field=text_field,
        source_field=source_field,
        domain_field=domain_field,
    )


def run_multilingual_ingestion(
    config: DatasetEngineeringConfig | None = None,
    selected_pipelines: list[str] | None = None,
) -> dict[str, DatasetStats]:
    pipeline = DatasetEngineeringPipeline(config)
    if selected_pipelines:
        pipeline_map = {
            "web": WebCrawlPipeline,
            "wiki": WikipediaPipeline,
            "books": BooksPipeline,
            "academic": AcademicPipeline,
            "code": CodePipeline,
            "math": MathPipeline,
            "qa": QAPipeline,
            "conversations": ConversationPipeline,
            "ocr": OcrPipeline,
            "image_caption": ImageCaptionPipeline,
            "multilingual": MultilingualPipeline,
        }
        results: dict[str, DatasetStats] = {}
        for name in selected_pipelines:
            if name in pipeline_map:
                p = pipeline_map[name](pipeline.config)
                try:
                    stats = pipeline.run_ingestion(p)
                    results[name] = stats
                except Exception as exc:
                    logger.error("Pipeline %s failed: %s", name, exc)
                    results[name] = DatasetStats()
        return results
    return pipeline.run_all()
