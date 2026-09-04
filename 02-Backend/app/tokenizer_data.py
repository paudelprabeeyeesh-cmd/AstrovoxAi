"""
Custom tokenizer training and data pipeline (Stage 40 Program 3).

Implements:
  * BPE (Byte Pair Encoding) tokenizer from scratch
  * Word-level tokenizer with normalization
  * Streaming dataset with quality filtering
  * Data deduplication (hash-based + n-gram)
  * Dataset versioning
  * Data lineage tracking
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Tuple

from .security_hardening import AuditLog, get_audit_log


# ---------------------------------------------------------------------------
# Tokenizer base
# ---------------------------------------------------------------------------


@dataclass
class TokenizerConfig:
    vocab_size: int = 32000
    min_pair_freq: int = 2
    lowercase: bool = True
    max_token_length: int = 64
    pattern: str = r"\w+|[^\w\s]"  # words or single punctuation


class Tokenizer:
    """BPE-style subword tokenizer trained from a corpus."""

    def __init__(self, config: Optional[TokenizerConfig] = None) -> None:
        self.config = config or TokenizerConfig()
        self.vocab: Dict[str, int] = {}
        self.inverse_vocab: Dict[int, str] = {}
        self.merges: List[Tuple[str, str]] = []

    @property
    def vocab_size(self) -> int:
        return len(self.vocab)

    def _pre_tokenize(self, text: str) -> List[str]:
        if self.config.lowercase:
            text = text.lower()
        text = unicodedata.normalize("NFKC", text)
        tokens = re.findall(self.config.pattern, text)
        result: List[str] = []
        for tok in tokens:
            if len(tok) > self.config.max_token_length:
                result.extend(
                    [tok[i : i + self.config.max_token_length] for i in range(0, len(tok), self.config.max_token_length)]
                )
            else:
                result.append(tok)
        return result

    def _get_pairs(self, word: List[str]) -> List[Tuple[str, str]]:
        pairs = set()
        prev = word[0]
        for ch in word[1:]:
            pairs.add((prev, ch))
            prev = ch
        return sorted(pairs)

    def train(self, corpus: Iterable[str]) -> "Tokenizer":
        token_freqs: Counter = Counter()
        for text in corpus:
            for token in self._pre_tokenize(text):
                token_freqs[token] += 1

        # Initial vocab: characters
        vocab: Dict[str, int] = {}
        for token in token_freqs:
            for ch in token:
                if ch not in vocab:
                    vocab[ch] = len(vocab)

        splits: Dict[str, List[str]] = {
            token: list(token) for token in token_freqs
        }
        merges: List[Tuple[str, str]] = []

        while len(vocab) < self.config.vocab_size:
            pair_freqs: Counter = Counter()
            for token, freq in token_freqs.items():
                split = splits[token]
                if len(split) < 2:
                    continue
                for pair in self._get_pairs(split):
                    pair_freqs[pair] += freq

            if not pair_freqs:
                break
            best_pair, best_freq = pair_freqs.most_common(1)[0]
            if best_freq < self.config.min_pair_freq:
                break

            merges.append(best_pair)
            new_token = best_pair[0] + best_pair[1]
            if new_token not in vocab:
                vocab[new_token] = len(vocab)
            for token in list(splits.keys()):
                split = splits[token]
                new_split: List[str] = []
                i = 0
                while i < len(split):
                    if i < len(split) - 1 and (split[i], split[i + 1]) == best_pair:
                        new_split.append(new_token)
                        i += 2
                    else:
                        new_split.append(split[i])
                        i += 1
                splits[token] = new_split

        self.vocab = vocab
        self.inverse_vocab = {idx: tok for tok, idx in vocab.items()}
        self.merges = merges
        return self

    def encode(self, text: str) -> List[int]:
        tokens = self._pre_tokenize(text)
        result: List[int] = []
        for token in tokens:
            split = list(token)
            for merge in self.merges:
                new_split: List[str] = []
                i = 0
                while i < len(split):
                    if i < len(split) - 1 and (split[i], split[i + 1]) == merge:
                        new_split.append(merge[0] + merge[1])
                        i += 2
                    else:
                        new_split.append(split[i])
                        i += 1
                split = new_split
            for sub in split:
                result.append(self.vocab.get(sub, self.vocab.get("<unk>", 0)))
        return result

    def decode(self, ids: List[int]) -> str:
        tokens = [self.inverse_vocab.get(i, "<unk>") for i in ids]
        return "".join(tokens)

    def save(self) -> Dict[str, Any]:
        return {
            "vocab": self.vocab,
            "merges": self.merges,
            "config": self.config.__dict__,
        }

    def load(self, data: Dict[str, Any]) -> None:
        self.vocab = {k: int(v) for k, v in data["vocab"].items()}
        self.inverse_vocab = {idx: tok for tok, idx in self.vocab.items()}
        self.merges = [tuple(m) for m in data["merges"]]
        cfg = data.get("config", {})
        self.config = TokenizerConfig(**cfg)


# ---------------------------------------------------------------------------
# Data pipeline
# ---------------------------------------------------------------------------


@dataclass
class Document:
    id: str
    text: str
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=lambda: __import__("time").time())


class TextCleaner:
    """Text normalization and cleaning pipeline."""

    def __init__(
        self,
        *,
        normalize_unicode: bool = True,
        remove_control: bool = True,
        collapse_whitespace: bool = True,
        min_length: int = 10,
        max_length: int = 100_000,
    ) -> None:
        self.normalize_unicode = normalize_unicode
        self.remove_control = remove_control
        self.collapse_whitespace = collapse_whitespace
        self.min_length = min_length
        self.max_length = max_length

    def clean(self, text: str) -> Optional[str]:
        if not text:
            return None
        if self.normalize_unicode:
            text = unicodedata.normalize("NFKC", text)
        if self.remove_control:
            text = "".join(ch for ch in text if unicodedata.category(ch)[0] != "C" or ch in "\n\t")
        if self.collapse_whitespace:
            text = re.sub(r"\s+", " ", text).strip()
        if len(text) < self.min_length or len(text) > self.max_length:
            return None
        return text


class QualityFilter:
    """Score documents by simple heuristics and reject low-quality ones."""

    def __init__(
        self,
        *,
        min_avg_word_length: float = 2.0,
        max_symbol_ratio: float = 0.4,
        min_alpha_ratio: float = 0.5,
    ) -> None:
        self.min_avg_word_length = min_avg_word_length
        self.max_symbol_ratio = max_symbol_ratio
        self.min_alpha_ratio = min_alpha_ratio

    def score(self, text: str) -> float:
        if not text:
            return 0.0
        words = text.split()
        if not words:
            return 0.0
        avg_word_length = sum(len(w) for w in words) / len(words)
        if avg_word_length < self.min_avg_word_length:
            return 0.0
        symbol_count = sum(1 for ch in text if not ch.isalnum() and not ch.isspace())
        symbol_ratio = symbol_count / max(len(text), 1)
        if symbol_ratio > self.max_symbol_ratio:
            return 0.0
        alpha_count = sum(1 for ch in text if ch.isalpha())
        alpha_ratio = alpha_count / max(len(text), 1)
        if alpha_ratio < self.min_alpha_ratio:
            return 0.0
        # Composite score
        return min(1.0, avg_word_length / 6.0) * (1.0 - symbol_ratio)

    def accept(self, text: str, threshold: float = 0.3) -> bool:
        return self.score(text) >= threshold


class Deduplicator:
    """Remove near-duplicate documents using hashes and n-gram overlap."""

    def __init__(self, *, ngram_size: int = 5) -> None:
        self.ngram_size = ngram_size
        self._seen_hashes: set = set()
        self._seen_ngrams: Dict[str, int] = {}

    @staticmethod
    def text_hash(text: str) -> str:
        return hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()

    def _ngrams(self, text: str) -> set:
        words = text.lower().split()
        if len(words) < self.ngram_size:
            return {" ".join(words)}
        return {" ".join(words[i : i + self.ngram_size]) for i in range(len(words) - self.ngram_size + 1)}

    def is_duplicate(self, text: str) -> bool:
        h = self.text_hash(text)
        if h in self._seen_hashes:
            return True
        self._seen_hashes.add(h)
        ngrams = self._ngrams(text)
        overlap = sum(1 for ng in ngrams if ng in self._seen_ngrams)
        if overlap > len(ngrams) * 0.8 and len(ngrams) > 0:
            return True
        for ng in ngrams:
            self._seen_ngrams[ng] = self._seen_ngrams.get(ng, 0) + 1
        return False


@dataclass
class DatasetVersion:
    version: str
    num_documents: int
    num_tokens: int
    created_at: float
    parent_version: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class DatasetRegistry:
    """Track dataset versions and lineage."""

    def __init__(self) -> None:
        self._versions: Dict[str, DatasetVersion] = {}
        self._lineage: Dict[str, List[str]] = defaultdict(list)
        self._audit: AuditLog = get_audit_log()

    def register(
        self,
        version: str,
        num_documents: int,
        num_tokens: int,
        parent_version: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DatasetVersion:
        import time as _time

        v = DatasetVersion(
            version=version,
            num_documents=num_documents,
            num_tokens=num_tokens,
            created_at=_time.time(),
            parent_version=parent_version,
            metadata=metadata or {},
        )
        self._versions[version] = v
        if parent_version:
            self._lineage[parent_version].append(version)
        self._audit.record(
            actor="dataset-pipeline",
            action="dataset_version_registered",
            target=version,
            metadata={"num_documents": num_documents, "num_tokens": num_tokens},
        )
        return v

    def get(self, version: str) -> Optional[DatasetVersion]:
        return self._versions.get(version)

    def lineage(self, version: str) -> List[str]:
        return list(self._lineage.get(version, []))

    def list(self) -> List[DatasetVersion]:
        return list(self._versions.values())


class StreamingDataset:
    """Stream documents through a clean → quality → dedup → tokenize pipeline."""

    def __init__(
        self,
        source: Iterable[Document],
        *,
        cleaner: Optional[TextCleaner] = None,
        quality: Optional[QualityFilter] = None,
        dedup: Optional[Deduplicator] = None,
    ) -> None:
        self.source = source
        self.cleaner = cleaner or TextCleaner()
        self.quality = quality or QualityFilter()
        self.dedup = dedup or Deduplicator()

    def __iter__(self) -> Iterator[Document]:
        for doc in self.source:
            cleaned = self.cleaner.clean(doc.text)
            if cleaned is None:
                continue
            if not self.quality.accept(cleaned):
                continue
            if self.dedup.is_duplicate(cleaned):
                continue
            yield Document(
                id=doc.id,
                text=cleaned,
                source=doc.source,
                metadata=doc.metadata,
                created_at=doc.created_at,
            )


# ---------------------------------------------------------------------------
# Tokenizer training pipeline
# ---------------------------------------------------------------------------


@dataclass
class TokenizerTrainingResult:
    tokenizer: Tokenizer
    corpus_size: int
    num_merges: int
    vocab_size: int
    training_time_s: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "corpus_size": self.corpus_size,
            "num_merges": self.num_merges,
            "vocab_size": self.vocab_size,
            "training_time_s": round(self.training_time_s, 2),
        }


def train_tokenizer(corpus: Iterable[str], config: Optional[TokenizerConfig] = None) -> TokenizerTrainingResult:
    import time as _time

    start = _time.time()
    tokenizer = Tokenizer(config)
    texts = list(corpus)
    corpus_size = sum(len(t) for t in texts)
    tokenizer.train(texts)
    end = _time.time()
    return TokenizerTrainingResult(
        tokenizer=tokenizer,
        corpus_size=corpus_size,
        num_merges=len(tokenizer.merges),
        vocab_size=tokenizer.vocab_size,
        training_time_s=end - start,
    )
