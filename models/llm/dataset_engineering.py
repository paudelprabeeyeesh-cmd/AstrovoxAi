"""
Phase 2 Dataset Engineering Module

Provides deduplication, filtering, cleaning, quality scoring,
language detection, PII removal, and domain balancing for
large-scale text datasets. Supports txt, jsonl, and parquet
formats with streaming for large files.
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import math
import os
import random
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional dependencies with graceful fallbacks
# ---------------------------------------------------------------------------
try:
    from datasketch import MinHash, MinHashLSH
    _HAS_MINHASH = True
except Exception:  # pragma: no cover - optional
    _HAS_MINHASH = False
    logger.debug("datasketch not available; near-duplicate removal disabled")

try:
    from langdetect import DetectorFactory, detect_langs
    DetectorFactory.seed = 0
    _HAS_LANGDETECT = True
except Exception:  # pragma: no cover - optional
    _HAS_LANGDETECT = False
    logger.debug("langdetect not available; language detection disabled")

try:
    import pyarrow as pa
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
    logger.debug("tiktoken not available; perplexity scoring disabled")

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
    pii_removed: bool = False
    dedup_hash: str = ""


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
    domains: Dict[str, int] = field(default_factory=dict)
    languages: Dict[str, int] = field(default_factory=Counter)

    def merge(self, other: "DatasetStats") -> None:
        self.total_documents += other.total_documents
        self.kept_documents += other.kept_documents
        self.removed_exact_duplicates += other.removed_exact_duplicates
        self.removed_near_duplicates += other.removed_near_duplicates
        self.removed_toxicity += other.removed_toxicity
        self.removed_pii += other.removed_pii
        self.removed_quality += other.removed_quality
        self.removed_language += other.removed_language
        for domain, count in other.domains.items():
            self.domains[domain] = self.domains.get(domain, 0) + count
        self.languages.update(other.languages)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class DedupConfig:
    enabled: bool = True
    exact_hash_field: str = "text"
    near_duplicate: bool = True
    near_dup_threshold: float = 0.75
    near_dup_shingle_size: int = 5
    near_dup_num_perm: int = 128


@dataclass
class ToxicityConfig:
    enabled: bool = True
    max_toxicity_score: float = 0.3
    profanity_tokens: List[str] = field(
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
        ]
    )


@dataclass
class QualityConfig:
    enabled: bool = True
    min_quality_score: float = 0.2
    use_perplexity: bool = True
    perplexity_model: Optional[str] = None
    length_normalization: bool = True
    diversity_weight: float = 0.3
    min_length: int = 20
    max_length: int = 100_000


@dataclass
class LanguageConfig:
    enabled: bool = True
    allowed_languages: List[str] = field(default_factory=lambda: ["en"])
    default_language: str = "en"
    confidence_threshold: float = 0.5


@dataclass
class PiiConfig:
    enabled: bool = True
    strip_email: bool = True
    strip_phone: bool = True
    strip_ip: bool = True
    strip_ssn: bool = True
    replacement: str = "[REDACTED]"


@dataclass
class DatasetEngineeringConfig:
    dedup: DedupConfig = field(default_factory=DedupConfig)
    toxicity: ToxicityConfig = field(default_factory=ToxicityConfig)
    quality: QualityConfig = field(default_factory=QualityConfig)
    language: LanguageConfig = field(default_factory=LanguageConfig)
    pii: PiiConfig = field(default_factory=PiiConfig)
    domain: str = "general"
    source: str = "unknown"
    seed: int = 42
    streaming_chunk_size: int = 10_000


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


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

class Deduplicator:
    def __init__(self, config: DedupConfig) -> None:
        self.config = config
        self.seen_hashes: set[str] = set()
        self.lsh: Optional[Any] = None
        if config.enabled and config.near_duplicate and _HAS_MINHASH:
            self.lsh = MinHashLSH(
                threshold=config.near_dup_threshold,
                num_perm=config.near_dup_num_perm,
            )
        self.removed_exact = 0
        self.removed_near = 0

    def _minhash(self, text: str) -> Optional[Any]:
        if not _HAS_MINHASH:
            return None
        m = MinHash(num_perm=self.config.near_dup_num_perm)
        for shingle in TextUtils.shingles(text, self.config.near_dup_shingle_size):
            m.update(shingle.encode("utf-8"))
        return m

    def process(self, document: ProcessedDocument) -> Optional[ProcessedDocument]:
        if not self.config.enabled:
            return document

        text = getattr(document, self.config.exact_hash_field, document.text)
        normalized = TextUtils.normalize(text)
        doc_hash = TextUtils.sha256(normalized)

        if doc_hash in self.seen_hashes:
            self.removed_exact += 1
            return None

        self.seen_hashes.add(doc_hash)

        if self.lsh is not None:
            m = self._minhash(normalized)
            if m is not None:
                matches = self.lsh.query(m)
                if matches:
                    self.removed_near += 1
                    return None
                self.lsh.insert(doc_hash, m)

        document.dedup_hash = doc_hash
        return document


# ---------------------------------------------------------------------------
# Toxicity filtering
# ---------------------------------------------------------------------------

class ToxicityFilter:
    def __init__(self, config: ToxicityConfig) -> None:
        self.config = config
        pattern = r"\b(" + "|".join(re.escape(t) for t in config.profanity_tokens) + r")\b"
        self._regex = re.compile(pattern, re.IGNORECASE)
        self.removed = 0

    def _score(self, text: str) -> float:
        matches = self._regex.findall(text)
        if not matches:
            return 0.0
        tokens = len(re.findall(r"\w+", text))
        if tokens == 0:
            return 1.0
        return min(1.0, len(matches) / (tokens * 0.1))

    def process(self, document: ProcessedDocument) -> Optional[ProcessedDocument]:
        if not self.config.enabled:
            return document
        score = self._score(document.text)
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

    def score(self, document: ProcessedDocument) -> float:
        text = document.text
        length = len(text.split())
        if length < self.config.min_length or length > self.config.max_length:
            return 0.0

        length_score = 1.0
        if self.config.length_normalization:
            ideal = 200
            length_score = math.exp(-((length - ideal) ** 2) / (2 * (ideal ** 2)))

        diversity_score = TextUtils.type_token_ratio(text)

        perplexity = self._perplexity(text)
        perplexity_score = max(0.0, min(1.0, 1.0 - (perplexity / 200.0)))

        quality = (
            (1.0 - self.config.diversity_weight) * perplexity_score
            + self.config.diversity_weight * diversity_score
        ) * length_score

        return max(0.0, min(1.0, quality))

    def process(self, document: ProcessedDocument) -> Optional[ProcessedDocument]:
        if not self.config.enabled:
            document.quality_score = 1.0
            return document
        document.quality_score = self.score(document)
        if document.quality_score < self.config.min_quality_score:
            return None
        return document


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

class LanguageDetector:
    def __init__(self, config: LanguageConfig) -> None:
        self.config = config

    def detect(self, text: str) -> Tuple[str, float]:
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

    def process(self, document: ProcessedDocument) -> Optional[ProcessedDocument]:
        if not self.config.enabled:
            return document
        lang, confidence = self.detect(document.text)
        document.language = lang
        if confidence < self.config.confidence_threshold:
            document.language = self.config.default_language
        if document.language not in self.config.allowed_languages:
            return None
        return document


# ---------------------------------------------------------------------------
# PII removal
# ---------------------------------------------------------------------------

class PiiRemover:
    _EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    _PHONE_RE = re.compile(
        r"(?:(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})"
    )
    _IP_RE = re.compile(
        r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
    )
    _SSN_RE = re.compile(
        r"\b\d{3}-\d{2}-\d{4}\b"
    )

    def __init__(self, config: PiiConfig) -> None:
        self.config = config
        self.removed_count = 0

    def _replace(self, text: str) -> Tuple[str, bool]:
        original = text
        if self.config.strip_email:
            text = self._EMAIL_RE.sub(self.config.replacement, text)
        if self.config.strip_phone:
            text = self._PHONE_RE.sub(self.config.replacement, text)
        if self.config.strip_ip:
            text = self._IP_RE.sub(self.config.replacement, text)
        if self.config.strip_ssn:
            text = self._SSN_RE.sub(self.config.replacement, text)
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
# Cleaners
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

    def process(self, document: ProcessedDocument) -> ProcessedDocument:
        text = document.text
        text = self._WIKI_MARKUP.sub("", text)
        text = self._INFOBOX.sub("", text)
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


# ---------------------------------------------------------------------------
# Domain balancing
# ---------------------------------------------------------------------------

class DomainBalancer:
    DOMAINS = [
        "books",
        "wiki",
        "common_crawl",
        "github",
        "docs",
        "stackoverflow",
        "math",
        "research",
        "conversations",
        "instructions",
    ]

    def __init__(self, target_ratios: Optional[Dict[str, float]] = None) -> None:
        if target_ratios is None:
            target_ratios = {d: 1.0 / len(self.DOMAINS) for d in self.DOMAINS}
        self.target_ratios = target_ratios
        self.buffers: Dict[str, List[ProcessedDocument]] = {d: [] for d in self.DOMAINS}
        self.total_seen = 0

    def add(self, document: ProcessedDocument) -> None:
        domain = document.domain or "general"
        if domain not in self.buffers:
            domain = "general"
        self.buffers[domain].append(document)
        self.total_seen += 1

    def sample(self) -> Iterator[ProcessedDocument]:
        if self.total_seen == 0:
            return
        counts = {d: len(v) for d, v in self.buffers.items()}
        for domain, docs in self.buffers.items():
            target = self.target_ratios.get(domain, 0.0)
            desired = int(self.total_seen * target)
            if len(docs) > desired:
                random.shuffle(docs)
                docs = docs[:desired]
            yield from docs


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
    def _read_jsonl(path: Path, chunk_size: int) -> Iterator[Dict[str, Any]]:
        if _HAS_IJSON:
            with path.open("rb") as f:
                for item in ijson.items(f, "item"):
                    yield item
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
    def _read_parquet(path: Path) -> Iterator[Dict[str, Any]]:
        if not _HAS_PYARROW:
            raise ImportError("pyarrow is required for parquet support")
        table = pq.read_table(str(path))
        df = table.to_pandas()
        for _, row in df.iterrows():
            yield row.to_dict()

    @staticmethod
    def iter_documents(
        path: Union[str, Path],
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
                    text=text,
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
        path: Union[str, Path],
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
                    "pii_removed": doc.pii_removed,
                    "dedup_hash": doc.dedup_hash,
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class DatasetEngineeringPipeline:
    def __init__(self, config: Optional[DatasetEngineeringConfig] = None) -> None:
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
        self.balancer = DomainBalancer()
        self.stats = DatasetStats()

    def _select_cleaner(self, domain: str) -> Callable[[ProcessedDocument], ProcessedDocument]:
        domain = domain.lower()
        if domain == "math":
            return self.math_cleaner.process
        if domain == "wiki":
            return self.wiki_cleaner.process
        if domain == "books":
            return self.books_cleaner.process
        if domain in {"github", "docs", "stackoverflow"}:
            return self.code_cleaner.process
        return lambda d: d

    def process_document(self, document: ProcessedDocument) -> Optional[ProcessedDocument]:
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

        self.stats.domains[document.domain] = self.stats.domains.get(document.domain, 0) + 1
        self.stats.languages[document.language] += 1
        self.stats.kept_documents += 1
        return document

    def process_stream(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        text_field: str = "text",
        source_field: str = "source",
        domain_field: str = "domain",
    ) -> DatasetStats:
        self.stats = DatasetStats()
        documents: List[ProcessedDocument] = []

        for document in DatasetIO.iter_documents(
            input_path,
            text_field=text_field,
            source_field=source_field,
            domain_field=domain_field,
            chunk_size=self.config.streaming_chunk_size,
        ):
            self.stats.total_documents += 1
            processed = self.process_document(document)
            if processed is not None:
                documents.append(processed)

            if len(documents) >= self.config.streaming_chunk_size:
                balanced = self.balancer.sample()
                DatasetIO.write_jsonl(balanced, output_path)
                documents = []

        if documents:
            balanced = self.balancer.sample()
            DatasetIO.write_jsonl(balanced, output_path)

        return self.stats


# ---------------------------------------------------------------------------
# Convenience API
# ---------------------------------------------------------------------------

def run_dataset_engineering(
    input_path: Union[str, Path],
    output_path: Union[str, Path],
    config: Optional[DatasetEngineeringConfig] = None,
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
