import asyncio
import hashlib
import io
import itertools
import json
import logging
import os
import random
import re
import statistics
import time
import unicodedata
from collections import Counter, deque
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import (
    Any,
)

logger = logging.getLogger(__name__)

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from bs4 import BeautifulSoup

    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

try:
    from datasets import load_dataset, load_from_disk

    HF_DATASETS_AVAILABLE = True
except ImportError:
    HF_DATASETS_AVAILABLE = False

try:
    from datasketch import MinHash, MinHashLSH

    DATASKETCH_AVAILABLE = True
except ImportError:
    DATASKETCH_AVAILABLE = False

try:
    from tqdm import tqdm

    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

try:
    import aiohttp

    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False


DOMAINS = [
    "books",
    "wikipedia",
    "common_crawl",
    "github",
    "docs",
    "stackoverflow",
    "math",
    "research",
    "conversations",
    "instructions",
]

DEFAULT_CURRICULUM_WEIGHTS: dict[str, float] = {
    "instructions": 1.4,
    "math": 1.3,
    "conversations": 1.2,
    "docs": 1.1,
    "research": 1.0,
    "wikipedia": 1.0,
    "books": 0.9,
    "github": 0.9,
    "stackoverflow": 0.85,
    "common_crawl": 0.7,
}

DEFAULT_MIN_LEN = 40
DEFAULT_MAX_LEN = 1_000_000
DEFAULT_QUALITY_THRESHOLD = 0.25


@dataclass
class PipelineConfig:
    output_path: str = "dataset.jsonl"
    min_length: int = DEFAULT_MIN_LEN
    max_length: int = DEFAULT_MAX_LEN
    quality_threshold: float = DEFAULT_QUALITY_THRESHOLD
    dedup_threshold: float = 0.80
    dedup_bands: int = 20
    max_samples: int | None = None
    seed: int = 42
    curriculum_weights: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_CURRICULUM_WEIGHTS)
    )
    sources: list[str] = field(default_factory=lambda: list(DOMAINS))
    validation_split: float = 0.02
    logging_interval: int = 5000
    stats_path: str = "pipeline_stats.json"
    enable_validation: bool = True
    strip_html: bool = True
    remove_spam: bool = True
    perplexity_model_name: str | None = None
    streaming_buffer_size: int = 10000


@dataclass
class Sample:
    text: str
    source: str
    quality_score: float = 0.0
    domain: str = ""
    length: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_jsonl(self) -> str:
        payload = {
            "text": self.text,
            "source": self.source,
            "quality_score": round(float(self.quality_score), 6),
        }
        if self.domain:
            payload["domain"] = self.domain
        if self.metadata:
            payload["metadata"] = self.metadata
        return json.dumps(payload, ensure_ascii=False)


def _ensure_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def _set_default_logging(level: int = logging.INFO) -> None:
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


class TextCleaner:
    HTML_TAG_RE = re.compile(r"<[^>]+>")
    MARKDOWN_LINK_RE = re.compile(r"\[.*?\]\(.*?\)")
    MARKDOWN_IMAGE_RE = re.compile(r"!\[.*?\]\(.*?\)")
    CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
    INLINE_CODE_RE = re.compile(r"`[^`]+`")
    HEADING_RE = re.compile(r"^#{1,6}\s+", re.MULTILINE)
    RULE_RE = re.compile(r"[-*_]{3,}")
    URL_RE = re.compile(r"https?://\S+|www\.\S+")
    EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
    CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
    WHITESPACE_RE = re.compile(r"\r\n|\r")
    SPACES_RE = re.compile(r"[ \t]+")
    NEWLINES_RE = re.compile(r"\n{3,}")
    SPAM_PHRASES = [
        "buy now",
        "click here",
        "subscribe now",
        "free trial",
        "limited time offer",
        "act now",
        "call now",
        "click below",
        "check this out",
        "exclusive offer",
    ]

    def __init__(
        self,
        min_length: int = DEFAULT_MIN_LEN,
        max_length: int = DEFAULT_MAX_LEN,
        strip_html: bool = True,
        remove_spam: bool = True,
    ):
        self.min_length = min_length
        self.max_length = max_length
        self.strip_html = strip_html
        self.remove_spam = remove_spam
        self._spam_pattern = self._compile_spam_pattern()

    def _compile_spam_pattern(self) -> re.Pattern | None:
        if not self.remove_spam or not self.SPAM_PHRASES:
            return None
            return re.compile("|".join(re.escape(p) for p in self.SPAM_PHRASES), re.IGNORECASE)

    def strip_html(self, text: str) -> str:
        if BS4_AVAILABLE:
            try:
                text = BeautifulSoup(text, "html.parser").get_text(separator=" ")
            except Exception:
                text = self.HTML_TAG_RE.sub(" ", text)
        elif self.strip_html:
            text = self.HTML_TAG_RE.sub(" ", text)
        return text

    def remove_markdown_artifacts(self, text: str) -> str:
        text = self.MARKDOWN_LINK_RE.sub("", text)
        text = self.MARKDOWN_IMAGE_RE.sub("", text)
        text = self.CODE_FENCE_RE.sub("", text)
        text = self.INLINE_CODE_RE.sub("", text)
        text = self.HEADING_RE.sub("", text)
        text = self.RULE_RE.sub("", text)
        return text

    def normalize_whitespace(self, text: str) -> str:
        text = self.WHITESPACE_RE.sub("\n", text)
        text = self.SPACES_RE.sub(" ", text)
        text = self.NEWLINES_RE.sub("\n\n", text)
        return text.strip()

    def remove_control_chars(self, text: str) -> str:
        return "".join(ch for ch in text if unicodedata.category(ch)[0] != "C" or ch in "\n\t")

    def remove_urls(self, text: str) -> str:
        return self.URL_RE.sub("", text)

    def remove_emails(self, text: str) -> str:
        return self.EMAIL_RE.sub("", text)

    def filter_by_length(self, text: str) -> bool:
        return self.min_length <= len(text) <= self.max_length

    def filter_spam(self, text: str) -> bool:
        if not self.remove_spam or self._spam_pattern is None:
            return True
        return not bool(self._spam_pattern.search(text))

    def clean(self, text: str) -> str | None:
        if not isinstance(text, str):
            return None
        text = unicodedata.normalize("NFKC", text)
        text = self.remove_control_chars(text)
        if self.strip_html:
            text = self.strip_html(text)
        text = self.remove_markdown_artifacts(text)
        text = self.remove_urls(text)
        text = self.remove_emails(text)
        text = self.normalize_whitespace(text)
        if not self.filter_by_length(text):
            return None
        if not self.filter_spam(text):
            return None
        return text


class Deduplicator:
    def __init__(self, threshold: float = 0.80, bands: int = 20, seed: int = 42):
        if not DATASKETCH_AVAILABLE:
            raise ImportError(
                "datasketch is required for MinHash deduplication. Install it with: pip install datasketch"
            )
        self.threshold = threshold
        self.bands = bands
        self.seed = seed
        self.lsh = MinHashLSH(threshold=threshold, num_perm=bands * 8, seed=seed)
        self._seen_hashes: set = set()
        self._count = 0
        self._duplicates = 0

    def _get_minhash(self, text: str) -> MinHash:
        m = MinHash(num_perm=self.bands * 8, seed=self.seed)
        for shingle in self._shingle(text):
            m.update(shingle.encode("utf-8", errors="ignore"))
        return m

    @staticmethod
    def _shingle(text: str, k: int = 5) -> list[str]:
        tokens = re.findall(r"\w+", text.lower())
        if len(tokens) < k:
            return [" ".join(tokens)] if tokens else []
        return [" ".join(tokens[i : i + k]) for i in range(len(tokens) - k + 1)]

    def is_duplicate(self, text: str) -> bool:
        text_hash = hashlib.md5(text.encode("utf-8", errors="ignore")).hexdigest()
        if text_hash in self._seen_hashes:
            self._duplicates += 1
            return True
        self._seen_hashes.add(text_hash)
        self._count += 1
        if self._count % 10000 == 0:
            logger.debug("Processed %d samples, %d duplicates", self._count, self._duplicates)
            return False
        m = self._get_minhash(text)
        result = self.lsh.query(m)
        if result:
            self._duplicates += 1
            return True
        self.lsh.insert(text_hash, m)
        return False

    @property
    def stats(self) -> dict[str, int]:
        return {"processed": self._count, "duplicates": self._duplicates}


class NaiveDeduplicator:
    def __init__(self):
        self._seen: set = set()
        self._count = 0
        self._duplicates = 0

    def is_duplicate(self, text: str) -> bool:
        text_hash = hashlib.md5(text.encode("utf-8", errors="ignore")).hexdigest()
        if text_hash in self._seen:
            self._duplicates += 1
            return True
        self._seen.add(text_hash)
        self._count += 1
        return False

    @property
    def stats(self) -> dict[str, int]:
        return {"processed": self._count, "duplicates": self._duplicates}


class QualityScorer:
    def __init__(self, model_name: str | None = None):
        self.model_name = model_name
        self._model = None
        self._tokenizer = None
        self._length_mean: float | None = None
        self._length_std: float | None = None

    def _load_model(self):
        if self._model is not None or self.model_name is None:
            return
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer

            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModelForCausalLM.from_pretrained(self.model_name)
            logger.info("Loaded quality model: %s", self.model_name)
        except Exception as exc:
            logger.warning("Failed to load quality model '%s': %s", self.model_name, exc)
            self.model_name = None

    def fit_length_stats(self, samples: Iterable[str]) -> None:
        lengths = [len(s) for s in samples]
        if not lengths:
            return
        self._length_mean = statistics.mean(lengths)
        self._length_std = statistics.pstdev(lengths) or 1.0
        logger.info("Fitted length stats: mean=%.2f, std=%.2f", self._length_mean, self._length_std)

    def score(self, text: str, reference_lengths: list[int] | None = None) -> float:
        length_score = self._length_score(text, reference_lengths)
        diversity_score = self._diversity_score(text)
        perplexity_score = self._perplexity_score(text)
        return 0.4 * perplexity_score + 0.35 * length_score + 0.25 * diversity_score

    def _length_score(self, text: str, reference_lengths: list[int] | None = None) -> float:
        length = len(text)
        if reference_lengths:
            mean = statistics.mean(reference_lengths)
            std = statistics.pstdev(reference_lengths) or 1.0
        elif self._length_mean is not None:
            mean = self._length_mean
            std = self._length_std
        else:
            mean, std = 800.0, 600.0
        z = (length - mean) / std
        return max(0.0, min(1.0, 1.0 - abs(z) / 4.0))

    def _diversity_score(self, text: str) -> float:
        tokens = re.findall(r"\w+", text.lower())
        if len(tokens) < 5:
            return 0.1
        unique = len(set(tokens))
        total = len(tokens)
        type_token_ratio = unique / total
        return min(1.0, type_token_ratio * 2.0)

    def _perplexity_score(self, text: str) -> float:
        self._load_model()
        if self._model is None or self._tokenizer is None:
            return 0.5
        try:
            import torch

            inputs = self._tokenizer(text, return_tensors="pt", truncation=True, max_length=1024)
            with torch.no_grad():
                outputs = self._model(**inputs, labels=inputs["input_ids"])
            ppl = torch.exp(outputs.loss).item()
            return max(0.0, min(1.0, 100.0 / (ppl + 1e-6)))
        except Exception as exc:
            logger.debug("Perplexity scoring failed: %s", exc)
            return 0.5


class DomainBalancer:
    def __init__(self, target_weights: dict[str, float]):
        self.target_weights = dict(target_weights)
        self._counts: Counter = Counter()
        self._total = 0

    def register(self, domain: str) -> None:
        self._counts[domain] += 1
        self._total += 1

    def should_sample(self, domain: str) -> bool:
        if self._total < 1000:
            return True
        current_weight = self.target_weights.get(domain, 1.0)
        expected = self._total * current_weight / sum(self.target_weights.values())
        observed = self._counts.get(domain, 0)
        return observed < expected * 1.5

    @property
    def stats(self) -> dict[str, Any]:
        total = self._total or 1
        return {
            "total": self._total,
            "per_domain": dict(self._counts),
            "ratios": {d: round(c / total, 6) for d, c in self._counts.items()},
        }


class CurriculumSampler:
    def __init__(self, weights: dict[str, float], seed: int = 42):
        self.weights = weights
        self.seed = seed
        self._rng = random.Random(seed)
        self._domain_buffers: dict[str, deque] = {d: deque() for d in weights}
        self._global_buffer: deque = deque()

    def add(self, sample: Sample) -> None:
        domain = sample.domain or "common_crawl"
        buffer = self._domain_buffers.get(domain)
        if buffer is not None:
            buffer.append(sample)
        else:
            self._global_buffer.append(sample)

    def sample(self) -> Sample | None:
        domains = list(self._domain_buffers.keys())
        weights = [self.weights.get(d, 1.0) for d in domains]
        total = sum(weights)
        if total == 0:
            return None
        r = self._rng.uniform(0, total)
        cumulative = 0.0
        chosen = domains[-1]
        for domain, weight in zip(domains, weights, strict=False):
            cumulative += weight
            if r <= cumulative:
                chosen = domain
                break
        buffer = self._domain_buffers.get(chosen)
        if buffer:
            return buffer.popleft()
        if self._global_buffer:
            return self._global_buffer.popleft()
        return None

    def __len__(self) -> int:
        return sum(len(b) for b in self._domain_buffers.values()) + len(self._global_buffer)


class DataValidator:
    REQUIRED_FIELDS = {"text", "source", "quality_score"}
    MAX_BYTE_SIZE = 10 * 1024 * 1024

    def __init__(self, enable: bool = True):
        self.enable = enable
        self._valid = 0
        self._invalid = 0
        self._errors: Counter = Counter()

    def validate(self, record: dict[str, Any]) -> bool:
        if not self.enable:
            return True
        try:
            if not isinstance(record, dict):
                self._record_error("not_a_dict")
                return False
            missing = self.REQUIRED_FIELDS - record.keys()
            if missing:
                self._record_error(f"missing_fields:{','.join(sorted(missing))}")
                return False
            text = record.get("text", "")
            if not isinstance(text, str) or not text.strip():
                self._record_error("empty_text")
                return False
            size = len(json.dumps(record, ensure_ascii=False).encode("utf-8"))
            if size > self.MAX_BYTE_SIZE:
                self._record_error("record_too_large")
                return False
            if not isinstance(record.get("source"), str):
                self._record_error("invalid_source")
                return False
            try:
                float(record.get("quality_score", 0))
            except TypeError, ValueError:
                self._record_error("invalid_quality_score")
                return False
            self._valid += 1
            return True
        except Exception as exc:
            self._record_error(f"exception:{type(exc).__name__}")
            return False

    def _record_error(self, key: str) -> None:
        self._invalid += 1
        self._errors[key] += 1

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "valid": self._valid,
            "invalid": self._invalid,
            "errors": dict(self._errors.most_common(20)),
        }


class LocalFileSource:
    def __init__(
        self, paths: str | list[str], domain: str, cleaner: TextCleaner, encoding: str = "utf-8"
    ):
        if isinstance(paths, str):
            paths = [paths]
        self.paths = [Path(p) for p in paths]
        self.domain = domain
        self.cleaner = cleaner
        self.encoding = encoding
        self._stats = {"files_scanned": 0, "raw_samples": 0, "cleaned_samples": 0}

    def stream(self) -> Iterator[Sample]:
        for path in self.paths:
            if not path.exists():
                logger.warning("Local file not found: %s", path)
                continue
            self._stats["files_scanned"] += 1
            try:
                with path.open("r", encoding=self.encoding, errors="ignore") as f:
                    for line in f:
                        self._stats["raw_samples"] += 1
                        cleaned = self.cleaner.clean(line)
                        if cleaned is None:
                            continue
                        self._stats["cleaned_samples"] += 1
                        yield Sample(text=cleaned, source=str(path.name), domain=self.domain)
            except Exception as exc:
                logger.error("Failed reading %s: %s", path, exc)


class HuggingFaceSource:
    def __init__(
        self,
        dataset_name: str,
        config: str | None = None,
        split: str = "train",
        domain: str = "common_crawl",
        cleaner: TextCleaner | None = None,
        text_field: str = "text",
        source_field: str | None = None,
        max_samples: int | None = None,
    ):
        if not HF_DATASETS_AVAILABLE:
            raise ImportError("datasets library is required. Install it with: pip install datasets")
        self.dataset_name = dataset_name
        self.config = config
        self.split = split
        self.domain = domain
        self.cleaner = cleaner or TextCleaner()
        self.text_field = text_field
        self.source_field = source_field
        self.max_samples = max_samples
        self._stats = {"rows_streamed": 0, "cleaned_samples": 0}

    def stream(self) -> Iterator[Sample]:
        try:
            dataset = load_dataset(self.dataset_name, self.config, split=self.split, streaming=True)
        except Exception as exc:
            logger.error("Failed to load HuggingFace dataset %s: %s", self.dataset_name, exc)
            return
        for row in dataset:
            if self.max_samples is not None and self._stats["rows_streamed"] >= self.max_samples:
                break
            self._stats["rows_streamed"] += 1
            text = row.get(self.text_field) if isinstance(row, dict) else None
            if not text:
                continue
            cleaned = self.cleaner.clean(str(text))
            if cleaned is None:
                continue
            self._stats["cleaned_samples"] += 1
            source = (
                row[self.source_field]
                if self.source_field and isinstance(row, dict) and self.source_field in row
                else self.dataset_name
            )
            yield Sample(text=cleaned, source=str(source), domain=self.domain)

    @property
    def stats(self) -> dict[str, int]:
        return dict(self._stats)


class WebSource:
    def __init__(
        self,
        urls: list[str],
        domain: str,
        cleaner: TextCleaner | None = None,
        max_pages: int = 1000,
        concurrency: int = 4,
    ):
        if not REQUESTS_AVAILABLE:
            raise ImportError(
                "requests is required for web scraping. Install it with: pip install requests"
            )
        self.urls = list(urls)
        self.domain = domain
        self.cleaner = cleaner or TextCleaner()
        self.max_pages = max_pages
        self.concurrency = min(concurrency, max(1, len(urls)))
        self._stats = {"pages_crawled": 0, "samples_yielded": 0}

    def stream(self) -> Iterator[Sample]:
        if not self.urls:
            return
        if AIOHTTP_AVAILABLE:
            yield from self._stream_async()
        else:
            yield from self._stream_sync()

    def _stream_sync(self) -> Iterator[Sample]:
        for url in itertools.islice(self.urls, self.max_pages):
            self._stats["pages_crawled"] += 1
            try:
                response = requests.get(
                    url, timeout=15, headers={"User-Agent": "AstrovoxAi-Crawler/1.0"}
                )
                response.raise_for_status()
                text = self._extract_text(response.text)
                cleaned = self.cleaner.clean(text)
                if cleaned:
                    self._stats["samples_yielded"] += 1
                    yield Sample(text=cleaned, source=url, domain=self.domain)
            except Exception as exc:
                logger.debug("Web scrape failed for %s: %s", url, exc)

    def _stream_async(self) -> Iterator[Sample]:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                logger.debug("Async event loop is running; falling back to sync web scraping")
                yield from self._stream_sync()
                return
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        async def _fetch(session, url):
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as response:
                    response.raise_for_status()
                    text = await response.text()
                    return self._extract_text(text)
            except Exception as exc:
                logger.debug("Async web scrape failed for %s: %s", url, exc)
                return None

        async def _run():
            semaphore = asyncio.Semaphore(self.concurrency)
            async with aiohttp.ClientSession(
                headers={"User-Agent": "AstrovoxAi-Crawler/1.0"}
            ) as session:
                tasks = []
                for url in itertools.islice(self.urls, self.max_pages):

                    async def _guarded(u=url):
                        async with semaphore:
                            return await _fetch(session, u)

                    tasks.append(_guarded())
                for coro in asyncio.as_completed(tasks):
                    text = await coro
                    if text is None:
                        continue
                    cleaned = self.cleaner.clean(text)
                    if cleaned:
                        self._stats["samples_yielded"] += 1
                        yield Sample(text=cleaned, source="web", domain=self.domain)

        try:
            gen = _run()
            loop.run_until_complete(gen.__anext__())
        except StopAsyncIteration:
            pass
        except Exception as exc:
            logger.error("Async web scraping failed: %s", exc)
            yield from self._stream_sync()
            return
        try:
            while True:
                yield loop.run_until_complete(gen.__anext__())
        except StopAsyncIteration:
            pass

    @staticmethod
    def _extract_text(html: str) -> str:
        if BS4_AVAILABLE:
            try:
                soup = BeautifulSoup(html, "html.parser")
                for tag in soup(["script", "style", "nav", "footer", "header"]):
                    tag.decompose()
                return soup.get_text(separator="\n")
            except Exception:
                pass
        return re.sub(r"<[^>]+>", " ", html)

    @property
    def stats(self) -> dict[str, int]:
        return dict(self._stats)


class DatasetPipeline:
    def __init__(self, config: PipelineConfig | None = None):
        self.config = config or PipelineConfig()
        random.seed(self.config.seed)
        self.cleaner = TextCleaner(
            min_length=self.config.min_length,
            max_length=self.config.max_length,
            strip_html=self.config.strip_html,
            remove_spam=self.config.remove_spam,
        )
        self.balancer = DomainBalancer(self.config.curriculum_weights)
        self.scorer = QualityScorer(model_name=self.config.perplexity_model_name)
        self.validator = DataValidator(enable=self.config.enable_validation)
        self.sampler = CurriculumSampler(self.config.curriculum_weights, seed=self.config.seed)
        self._stats = {
            "total_raw": 0,
            "total_cleaned": 0,
            "total_deduped": 0,
            "total_validated": 0,
            "total_written": 0,
            "domains": Counter(),
            "sources": Counter(),
            "quality_scores": [],
            "start_time": time.time(),
            "end_time": None,
        }
        self._deduplicator: Deduplicator | NaiveDeduplicator | None = None
        self._output_handle = None
        self._train_handle = None
        self._val_handle = None

    def _get_deduplicator(self) -> Deduplicator | NaiveDeduplicator:
        if self._deduplicator is None:
            if DATASKETCH_AVAILABLE:
                try:
                    self._deduplicator = Deduplicator(
                        threshold=self.config.dedup_threshold,
                        bands=self.config.dedup_bands,
                        seed=self.config.seed,
                    )
                except Exception as exc:
                    logger.warning("Falling back to naive deduplication: %s", exc)
                    self._deduplicator = NaiveDeduplicator()
            else:
                logger.warning("datasketch not available; using naive MD5 deduplication")
                self._deduplicator = NaiveDeduplicator()
        return self._deduplicator

    def add_source(self, source: LocalFileSource | HuggingFaceSource | WebSource) -> None:
        if source.domain not in self.config.sources:
            logger.info("Skipping domain '%s' not in enabled sources", source.domain)
            return
        logger.info("Streaming from %s source: %s", source.domain, type(source).__name__)
        dedup = self._get_deduplicator()
        buffer: list[Sample] = []
        for sample in source.stream():
            self._stats["total_raw"] += 1
            buffer.append(sample)
            if len(buffer) >= self.config.streaming_buffer_size:
                self._process_buffer(buffer, dedup)
                buffer = []
        if buffer:
            self._process_buffer(buffer, dedup)
        if hasattr(source, "stats"):
            logger.debug("Source stats: %s", source.stats)

    def _process_buffer(
        self, buffer: list[Sample], dedup: Deduplicator | NaiveDeduplicator
    ) -> None:
        for sample in buffer:
            if not self.balancer.should_sample(sample.domain):
                continue
            if dedup.is_duplicate(sample.text):
                continue
            self._stats["total_deduped"] += 1
            sample.quality_score = self.scorer.score(sample.text)
            if sample.quality_score < self.config.quality_threshold:
                continue
            self._stats["total_cleaned"] += 1
            record = {
                "text": sample.text,
                "source": sample.source,
                "quality_score": round(float(sample.quality_score), 6),
                "domain": sample.domain,
            }
            if sample.metadata:
                record["metadata"] = sample.metadata
            if self.validator.validate(record):
                self._stats["total_validated"] += 1
                self.sampler.add(sample)
                self._stats["domains"][sample.domain] += 1
                self._stats["sources"][sample.source] += 1
                self._stats["quality_scores"].append(sample.quality_score)
                self.balancer.register(sample.domain)

    def write_jsonl(self, output_path: str | None = None) -> str:
        output_path = output_path or self.config.output_path
        os.makedirs(
            os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True
        )
        if self.config.validation_split > 0:
            self._write_split(output_path)
        else:
            with open(output_path, "w", encoding="utf-8") as f:
                self._write_samples(f)
        logger.info("Wrote dataset to %s", output_path)
        return output_path

    def _write_split(self, output_path: str) -> None:
        base, ext = os.path.splitext(output_path)
        train_path = f"{base}_train{ext}"
        val_path = f"{base}_val{ext}"
        with (
            open(train_path, "w", encoding="utf-8") as train_f,
            open(val_path, "w", encoding="utf-8") as val_f,
        ):
            val_ratio = self.config.validation_split
            for sample in self._sample_iter():
                self._stats["total_written"] += 1
                line = sample.to_jsonl()
                if random.random() < val_ratio:
                    val_f.write(line + "\n")
                else:
                    train_f.write(line + "\n")
        logger.info("Wrote train split: %s, val split: %s", train_path, val_path)

    def _write_samples(self, f: io.TextIOBase) -> None:
        for sample in self._sample_iter():
            self._stats["total_written"] += 1
            f.write(sample.to_jsonl() + "\n")

    def _sample_iter(self) -> Iterator[Sample]:
        while len(self.sampler) > 0:
            sample = self.sampler.sample()
            if sample is None:
                break
            yield sample

    def compute_statistics(self) -> dict[str, Any]:
        self._stats["end_time"] = time.time()
        elapsed = self._stats["end_time"] - self._stats["start_time"]
        quality_scores = self._stats["quality_scores"]
        stats = {
            "elapsed_seconds": round(elapsed, 2),
            "total_raw": self._stats["total_raw"],
            "total_cleaned": self._stats["total_cleaned"],
            "total_deduped": self._stats["total_deduped"],
            "total_validated": self._stats["total_validated"],
            "total_written": self._stats["total_written"],
            "throughput_samples_per_sec": round(self._stats["total_raw"] / max(elapsed, 1e-6), 2),
            "domains": dict(self._stats["domains"]),
            "sources_top": dict(self._stats["sources"].most_common(20)),
            "quality_score": {
                "mean": round(statistics.mean(quality_scores), 6) if quality_scores else 0.0,
                "median": round(statistics.median(quality_scores), 6) if quality_scores else 0.0,
                "std": round(statistics.pstdev(quality_scores), 6) if quality_scores else 0.0,
                "min": round(min(quality_scores), 6) if quality_scores else 0.0,
                "max": round(max(quality_scores), 6) if quality_scores else 0.0,
            },
            "deduplication": self._deduplicator.stats if self._deduplicator else {},
            "validator": self.validator.stats,
            "balancer": self.balancer.stats,
        }
        return stats

    def save_statistics(self, path: str | None = None) -> str:
        path = path or self.config.stats_path
        stats = self.compute_statistics()
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        logger.info("Statistics saved to %s", path)
        return path

    def run(
        self, sources: list[LocalFileSource | HuggingFaceSource | WebSource] | None = None
    ) -> str:
        _set_default_logging()
        logger.info("Starting dataset pipeline with config: %s", self.config.__dict__)
        if sources:
            for source in sources:
                self.add_source(source)
        output_path = self.write_jsonl()
        stats_path = self.save_statistics()
        logger.info("Pipeline complete. Output: %s, Stats: %s", output_path, stats_path)
        self._log_final_stats()
        return output_path

    def _log_final_stats(self) -> None:
        stats = self.compute_statistics()
        logger.info(
            "Pipeline stats: raw=%d, cleaned=%d, deduped=%d, validated=%d, written=%d, elapsed=%.2fs",
            stats["total_raw"],
            stats["total_cleaned"],
            stats["total_deduped"],
            stats["total_validated"],
            stats["total_written"],
            stats["elapsed_seconds"],
        )
        if stats["quality_scores"].get("mean"):
            logger.info(
                "Quality scores - mean: %.4f, median: %.4f, std: %.4f",
                stats["quality_scores"]["mean"],
                stats["quality_scores"]["median"],
                stats["quality_scores"]["std"],
            )


class StreamingDatasetPipeline:
    def __init__(self, config: PipelineConfig | None = None):
        self.config = config or PipelineConfig()
        self.pipeline = DatasetPipeline(config=self.config)

    def stream_jsonl(self, output_path: str | None = None) -> Iterator[str]:
        output_path = output_path or self.config.output_path
        os.makedirs(
            os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True
        )
        file_handle = open(output_path, "w", encoding="utf-8")
        try:
            for sample in self.pipeline._sample_iter():
                self.pipeline._stats["total_written"] += 1
                line = sample.to_jsonl()
                file_handle.write(line + "\n")
                file_handle.flush()
                yield line
        finally:
            file_handle.close()

    def run_streaming(
        self, sources: list[LocalFileSource | HuggingFaceSource | WebSource] | None = None
    ) -> str:
        _set_default_logging()
        logger.info("Starting streaming dataset pipeline")
        if sources:
            for source in sources:
                self.pipeline.add_source(source)
        output_path = self.pipeline.write_jsonl()
        self.pipeline.save_statistics()
        return output_path


def build_default_pipeline(
    output_path: str = "dataset.jsonl",
    local_paths: list[str] | None = None,
    hf_datasets: list[dict[str, Any]] | None = None,
    web_urls: dict[str, list[str]] | None = None,
    config: PipelineConfig | None = None,
) -> DatasetPipeline:
    cfg = config or PipelineConfig(output_path=output_path)
    pipeline = DatasetPipeline(config=cfg)
    if local_paths:
        for path in local_paths:
            domain = _guess_domain(path)
            pipeline.add_source(
                LocalFileSource(paths=[path], domain=domain, cleaner=pipeline.cleaner)
            )
    if hf_datasets:
        for ds in hf_datasets:
            domain = ds.get("domain", "common_crawl")
            source = HuggingFaceSource(
                dataset_name=ds["name"],
                config=ds.get("config"),
                split=ds.get("split", "train"),
                domain=domain,
                cleaner=pipeline.cleaner,
                text_field=ds.get("text_field", "text"),
                source_field=ds.get("source_field"),
                max_samples=ds.get("max_samples"),
            )
            pipeline.add_source(source)
    if web_urls:
        for domain, urls in web_urls.items():
            pipeline.add_source(
                WebSource(urls=urls, domain=domain, cleaner=pipeline.cleaner, max_pages=1000)
            )
    return pipeline


def _guess_domain(path: str) -> str:
    path_lower = path.lower()
    for domain in DOMAINS:
        if domain.replace("_", "") in path_lower.replace("_", "").replace("-", ""):
            return domain
    return "common_crawl"


def run_pipeline(
    output_path: str = "dataset.jsonl",
    sources: list[LocalFileSource | HuggingFaceSource | WebSource] | None = None,
    config: PipelineConfig | None = None,
) -> str:
    pipeline = DatasetPipeline(config=config or PipelineConfig(output_path=output_path))
    return pipeline.run(sources=sources)


def stream_pipeline(
    output_path: str = "dataset.jsonl",
    sources: list[LocalFileSource | HuggingFaceSource | WebSource] | None = None,
    config: PipelineConfig | None = None,
) -> Iterator[str]:
    sp = StreamingDatasetPipeline(config=config or PipelineConfig(output_path=output_path))
    if sources:
        for source in sources:
            sp.pipeline.add_source(source)
    yield from sp.stream_jsonl()
