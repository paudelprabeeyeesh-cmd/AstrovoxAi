"""Phase 3 tokenizer research module.

Provides a unified research surface over multiple tokenizer families,
online vocabulary operations, and benchmark suites.
"""

from __future__ import annotations

import collections
import contextlib
import json
import os
import statistics
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Optional heavy dependencies with graceful fallbacks
# ---------------------------------------------------------------------------
try:
    from tokenizers import Tokenizer as HFTokenizer
    from tokenizers.models import BPE, Unigram, WordPiece
    from tokenizers.pre_tokenizers import ByteLevel, Whitespace
    from tokenizers.processors import TemplateProcessing
    from tokenizers.trainers import BpeTrainer, WordPieceTrainer

    _TOKENIZERS_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    _TOKENIZERS_AVAILABLE = False

try:
    import sentencepiece as spm

    _SENTENCEPIECE_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    _SENTENCEPIECE_AVAILABLE = False


# ---------------------------------------------------------------------------
# Shared data structures
# ---------------------------------------------------------------------------
@dataclass
class TokenizerResult:
    """Standard encode/decode container."""

    ids: list[int] = field(default_factory=list)
    tokens: list[str] = field(default_factory=list)
    offsets: list[tuple[int, int]] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.ids)


@dataclass
class BenchmarkSample:
    text: str
    encoding_time_ms: float
    num_tokens: int
    num_chars: int
    num_bytes: int
    tokens: list[str] = field(default_factory=list)


@dataclass
class BenchmarkResult:
    name: str
    samples: list[BenchmarkSample] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total_texts(self) -> int:
        return len(self.samples)

    @property
    def total_tokens(self) -> int:
        return sum(s.num_tokens for s in self.samples)

    @property
    def total_chars(self) -> int:
        return sum(s.num_chars for s in self.samples)

    @property
    def total_bytes(self) -> int:
        return sum(s.num_bytes for s in self.samples)

    @property
    def total_encoding_time_ms(self) -> float:
        return sum(s.encoding_time_ms for s in self.samples)

    @property
    def avg_tokens_per_char(self) -> float:
        return self.total_tokens / self.total_chars if self.total_chars else 0.0

    @property
    def avg_tokens_per_byte(self) -> float:
        return self.total_tokens / self.total_bytes if self.total_bytes else 0.0

    @property
    def chars_per_token(self) -> float:
        return self.total_chars / self.total_tokens if self.total_tokens else 0.0

    @property
    def bytes_per_token(self) -> float:
        return self.total_bytes / self.total_tokens if self.total_tokens else 0.0

    @property
    def tokens_per_second(self) -> float:
        elapsed = self.total_encoding_time_ms / 1000.0
        return self.total_tokens / elapsed if elapsed > 0 else 0.0

    @property
    def texts_per_second(self) -> float:
        elapsed = self.total_encoding_time_ms / 1000.0
        return self.total_texts / elapsed if elapsed > 0 else 0.0

    def compression_ratio(self) -> float:
        return self.total_bytes / self.total_tokens if self.total_tokens else 0.0

    def oov_rate(self, reference_vocab: set[str]) -> float:
        oov = sum(1 for s in self.samples for tok in s.tokens if tok not in reference_vocab)
        return oov / self.total_tokens if self.total_tokens else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "metadata": self.metadata,
            "total_texts": self.total_texts,
            "total_tokens": self.total_tokens,
            "total_chars": self.total_chars,
            "total_bytes": self.total_bytes,
            "total_encoding_time_ms": round(self.total_encoding_time_ms, 4),
            "avg_tokens_per_char": round(self.avg_tokens_per_char, 6),
            "avg_tokens_per_byte": round(self.avg_tokens_per_byte, 6),
            "chars_per_token": round(self.chars_per_token, 6),
            "bytes_per_token": round(self.bytes_per_token, 6),
            "tokens_per_second": round(self.tokens_per_second, 2),
            "texts_per_second": round(self.texts_per_second, 2),
            "compression_ratio": round(self.compression_ratio(), 4),
        }


# ---------------------------------------------------------------------------
# Base tokenizer interface
# ---------------------------------------------------------------------------
class BaseTokenizer:
    name: str = "base"
    metadata: dict[str, Any] = field(default_factory=dict)

    def encode(self, text: str) -> TokenizerResult:
        raise NotImplementedError

    def decode(self, ids: list[int]) -> str:
        raise NotImplementedError

    def vocab_size(self) -> int:
        raise NotImplementedError

    def get_vocab(self) -> dict[str, int]:
        raise NotImplementedError

    def save(self, directory: str) -> None:
        raise NotImplementedError

    @classmethod
    def load(cls, directory: str) -> BaseTokenizer:
        raise NotImplementedError

    def _time_encode(self, text: str) -> tuple[TokenizerResult, float]:
        start = time.perf_counter()
        result = self.encode(text)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return result, elapsed_ms


# ---------------------------------------------------------------------------
# 1. BPE tokenizer (huggingface tokenizers backed)
# ---------------------------------------------------------------------------
class BPETokenizer(BaseTokenizer):
    name = "bpe"

    def __init__(
        self,
        vocab: dict[str, int] | None = None,
        merges: list[tuple[str, str]] | None = None,
        special_tokens: list[str] | None = None,
    ) -> None:
        self.special_tokens = special_tokens or ["<s>", "<pad>", "</s>", "<unk>"]
        self._vocab = dict(vocab) if vocab else {}
        self._merges = list(merges) if merges else []
        self._hf_tokenizer: HFTokenizer | None = None
        if _TOKENIZERS_AVAILABLE and self._vocab and self._merges:
            self._build_hf_tokenizer()

    def _build_hf_tokenizer(self) -> None:
        if not _TOKENIZERS_AVAILABLE:
            return
        try:
            hf = HFTokenizer(BPE(vocab=self._vocab, merges=self._merges, unk_token="<unk>"))
            hf.pre_tokenizer = ByteLevel()
            hf.post_processor = TemplateProcessing(
                single="<s> $0 </s>",
                special_tokens=[(tok, i) for i, tok in enumerate(self.special_tokens)],
            )
            hf.enable_truncation(max_length=2048)
            self._hf_tokenizer = hf
        except Exception:
            self._hf_tokenizer = None

    def encode(self, text: str) -> TokenizerResult:
        if self._hf_tokenizer is not None:
            try:
                encoded = self._hf_tokenizer.encode(text)
                return TokenizerResult(
                    ids=encoded.ids,
                    tokens=encoded.tokens,
                    offsets=[(s, e) for s, e in encoded.offsets],
                )
            except Exception:
                pass
        return self._encode_fallback(text)

    def _encode_fallback(self, text: str) -> TokenizerResult:
        tokens: list[str] = []
        ids: list[int] = []
        for chunk in self._split_text(text):
            if chunk in self._vocab:
                tokens.append(chunk)
                ids.append(self._vocab[chunk])
            else:
                for char in chunk:
                    char_tok = f"##{char}"
                    tokens.append(char_tok)
                    ids.append(self._vocab.get(char_tok, self._vocab.get("<unk>", 1)))
        return TokenizerResult(ids=ids, tokens=tokens)

    def _split_text(self, text: str) -> list[str]:
        tokens: list[str] = []
        i = 0
        while i < len(text):
            matched = False
            for j in range(len(text), i, -1):
                sub = text[i:j]
                if sub in self._vocab:
                    tokens.append(sub)
                    i = j
                    matched = True
                    break
            if not matched:
                tokens.append(text[i])
                i += 1
        return tokens

    def decode(self, ids: list[int]) -> str:
        if self._hf_tokenizer is not None:
            try:
                return self._hf_tokenizer.decode(ids)
            except Exception:
                pass
        inv = {v: k for k, v in self._vocab.items()}
        tokens = [inv.get(i, "<unk>") for i in ids]
        text = "".join(tokens).replace("##", "")
        return text

    def vocab_size(self) -> int:
        return len(self._vocab)

    def get_vocab(self) -> dict[str, int]:
        return dict(self._vocab)

    def save(self, directory: str) -> None:
        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, "vocab.json"), "w", encoding="utf-8") as f:
            json.dump(self._vocab, f, ensure_ascii=False, indent=2)
        with open(os.path.join(directory, "merges.txt"), "w", encoding="utf-8") as f:
            for left, right in self._merges:
                f.write(f"{left} {right}\n")

    @classmethod
    def load(cls, directory: str) -> BPETokenizer:
        vocab_path = os.path.join(directory, "vocab.json")
        merges_path = os.path.join(directory, "merges.txt")
        with open(vocab_path, encoding="utf-8") as f:
            vocab = json.load(f)
        merges: list[tuple[str, str]] = []
        if os.path.exists(merges_path):
            with open(merges_path, encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) == 2:
                        merges.append((parts[0], parts[1]))
        return cls(vocab=vocab, merges=merges)


# ---------------------------------------------------------------------------
# 2. SentencePiece wrapper
# ---------------------------------------------------------------------------
class SentencePieceTokenizer(BaseTokenizer):
    name = "sentencepiece"

    def __init__(self, model_path: str | None = None) -> None:
        self._model_path = model_path
        self._sp = None
        if model_path and os.path.exists(model_path):
            self._load()

    def _load(self) -> None:
        if not _SENTENCEPIECE_AVAILABLE:
            raise RuntimeError("sentencepiece is not installed.")
        self._sp = spm.SentencePieceProcessor()
        self._sp.load(self._model_path)

    def encode(self, text: str) -> TokenizerResult:
        if self._sp is None:
            raise RuntimeError("SentencePiece model not loaded.")
        ids = self._sp.encode(text, out_type=int)
        pieces = self._sp.encode(text, out_type=str)
        offsets = []
        start = 0
        for piece in pieces:
            end = start + len(piece)
            offsets.append((start, end))
            start = end
        return TokenizerResult(ids=ids, tokens=pieces, offsets=offsets)

    def decode(self, ids: list[int]) -> str:
        if self._sp is None:
            raise RuntimeError("SentencePiece model not loaded.")
        return self._sp.decode(ids.tolist() if hasattr(ids, "tolist") else list(ids))

    def vocab_size(self) -> int:
        return self._sp.get_piece_size() if self._sp is not None else 0

    def get_vocab(self) -> dict[str, int]:
        if self._sp is None:
            return {}
        return {self._sp.id_to_piece(i): i for i in range(self._sp.get_piece_size())}

    def save(self, directory: str) -> None:
        if self._model_path and os.path.exists(self._model_path):
            os.makedirs(directory, exist_ok=True)
            dest = os.path.join(directory, os.path.basename(self._model_path))
            import shutil

            shutil.copy2(self._model_path, dest)

    @classmethod
    def load(cls, directory: str) -> SentencePieceTokenizer:
        model_file = None
        for candidate in os.listdir(directory):
            if candidate.endswith(".model"):
                model_file = os.path.join(directory, candidate)
                break
        if model_file is None:
            raise FileNotFoundError("No SentencePiece .model file found.")
        return cls(model_path=model_file)


# ---------------------------------------------------------------------------
# 3. Unigram tokenizer (huggingface tokenizers backed)
# ---------------------------------------------------------------------------
class UnigramTokenizer(BaseTokenizer):
    name = "unigram"

    def __init__(
        self,
        vocab: dict[str, float] | None = None,
        special_tokens: list[str] | None = None,
    ) -> None:
        self.special_tokens = special_tokens or ["<s>", "<pad>", "</s>", "<unk>"]
        self._vocab = dict(vocab) if vocab else {}
        self._hf_tokenizer: HFTokenizer | None = None
        if _TOKENIZERS_AVAILABLE and self._vocab:
            self._build_hf_tokenizer()

    def _build_hf_tokenizer(self) -> None:
        if not _TOKENIZERS_AVAILABLE:
            return
        try:
            vocab_items = list(self._vocab.items())
            hf = HFTokenizer(
                Unigram(vocab=vocab_items, unk_id=self.special_tokens.index("<unk>"))
            )
            hf.pre_tokenizer = ByteLevel()
            hf.post_processor = TemplateProcessing(
                single="<s> $0 </s>",
                special_tokens=[(tok, i) for i, tok in enumerate(self.special_tokens)],
            )
            self._hf_tokenizer = hf
        except Exception:
            self._hf_tokenizer = None

    def encode(self, text: str) -> TokenizerResult:
        if self._hf_tokenizer is not None:
            try:
                encoded = self._hf_tokenizer.encode(text)
                return TokenizerResult(
                    ids=encoded.ids,
                    tokens=encoded.tokens,
                    offsets=[(s, e) for s, e in encoded.offsets],
                )
            except Exception:
                pass
        tokens = list(text)
        ids = [self._vocab.get(tok, self._vocab.get("<unk>", 1)) for tok in tokens]
        return TokenizerResult(ids=ids, tokens=tokens)

    def decode(self, ids: list[int]) -> str:
        if self._hf_tokenizer is not None:
            try:
                return self._hf_tokenizer.decode(ids)
            except Exception:
                pass
        inv = {v: k for k, v in self._vocab.items()}
        return "".join(inv.get(i, "<unk>") for i in ids)

    def vocab_size(self) -> int:
        return len(self._vocab)

    def get_vocab(self) -> dict[str, int]:
        return {k: i for i, k in enumerate(self._vocab.keys())}

    def save(self, directory: str) -> None:
        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, "vocab.json"), "w", encoding="utf-8") as f:
            json.dump(self._vocab, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, directory: str) -> UnigramTokenizer:
        with open(os.path.join(directory, "vocab.json"), encoding="utf-8") as f:
            vocab = json.load(f)
        return cls(vocab=vocab)


# ---------------------------------------------------------------------------
# 4. WordPiece tokenizer
# ---------------------------------------------------------------------------
class WordPieceTokenizer(BaseTokenizer):
    name = "wordpiece"

    def __init__(
        self,
        vocab: dict[str, int] | None = None,
        special_tokens: list[str] | None = None,
        unk_token: str = "[UNK]",
    ) -> None:
        self.special_tokens = special_tokens or ["[UNK]", "[CLS]", "[SEP]", "[PAD]", "[MASK]"]
        self.unk_token = unk_token
        self._vocab = dict(vocab) if vocab else {}
        self._hf_tokenizer: HFTokenizer | None = None
        if _TOKENIZERS_AVAILABLE and self._vocab:
            self._build_hf_tokenizer()

    def _build_hf_tokenizer(self) -> None:
        if not _TOKENIZERS_AVAILABLE:
            return
        try:
            hf = HFTokenizer(WordPiece(vocab=self._vocab, unk_token=self.unk_token))
            hf.pre_tokenizer = Whitespace()
            hf.post_processor = TemplateProcessing(
                single="[CLS] $0 [SEP]",
                special_tokens=[(tok, i) for i, tok in enumerate(self.special_tokens)],
            )
            self._hf_tokenizer = hf
        except Exception:
            self._hf_tokenizer = None

    def encode(self, text: str) -> TokenizerResult:
        if self._hf_tokenizer is not None:
            try:
                encoded = self._hf_tokenizer.encode(text)
                return TokenizerResult(
                    ids=encoded.ids,
                    tokens=encoded.tokens,
                    offsets=[(s, e) for s, e in encoded.offsets],
                )
            except Exception:
                pass
        tokens: list[str] = []
        ids: list[int] = []
        for word in text.split():
            sub_tokens = self._tokenize_word(word)
            tokens.extend(sub_tokens)
            ids.extend(self._vocab.get(t, self._vocab.get(self.unk_token, 1)) for t in sub_tokens)
        return TokenizerResult(ids=ids, tokens=tokens)

    def _tokenize_word(self, word: str) -> list[str]:
        if word in self._vocab:
            return [word]
        tokens: list[str] = []
        start = 0
        while start < len(word):
            end = len(word)
            cur = None
            while start < end:
                sub = word[start:end]
                if start > 0:
                    sub = "##" + sub
                if sub in self._vocab:
                    cur = sub
                    break
                end -= 1
            if cur is None:
                tokens.append(self.unk_token)
                break
            tokens.append(cur)
            start = end
        return tokens

    def decode(self, ids: list[int]) -> str:
        if self._hf_tokenizer is not None:
            try:
                return self._hf_tokenizer.decode(ids)
            except Exception:
                pass
        inv = {v: k for k, v in self._vocab.items()}
        words: list[str] = []
        current: list[str] = []
        for i in ids:
            tok = inv.get(i, self.unk_token)
            if tok.startswith("##"):
                current.append(tok[2:])
            else:
                if current:
                    words.append("".join(current))
                current = [tok]
        if current:
            words.append("".join(current))
        return " ".join(words)

    def vocab_size(self) -> int:
        return len(self._vocab)

    def get_vocab(self) -> dict[str, int]:
        return dict(self._vocab)

    def save(self, directory: str) -> None:
        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, "vocab.txt"), "w", encoding="utf-8") as f:
            for tok, _ in sorted(self._vocab.items(), key=lambda x: x[1]):
                f.write(f"{tok}\n")

    @classmethod
    def load(cls, directory: str) -> WordPieceTokenizer:
        vocab: dict[str, int] = {}
        with open(os.path.join(directory, "vocab.txt"), encoding="utf-8") as f:
            for i, line in enumerate(f):
                tok = line.rstrip("\n")
                vocab[tok] = i
        return cls(vocab=vocab)


# ---------------------------------------------------------------------------
# 5. Byte tokenizer
# ---------------------------------------------------------------------------
class ByteTokenizer(BaseTokenizer):
    name = "byte"

    def __init__(self, special_tokens: list[str] | None = None) -> None:
        self.special_tokens = special_tokens or ["<s>", "<pad>", "</s>", "<unk>"]
        self._vocab: dict[str, int] = {}
        self._inv_vocab: dict[int, str] = {}
        for i, tok in enumerate(self.special_tokens):
            self._vocab[tok] = i
            self._inv_vocab[i] = tok
        for i in range(256):
            tok = f"<0x{i:02X}>"
            idx = len(self._vocab)
            self._vocab[tok] = idx
            self._inv_vocab[idx] = tok

    def encode(self, text: str) -> TokenizerResult:
        ids: list[int] = []
        tokens: list[str] = []
        for ch in text:
            tok = f"<0x{ord(ch):02X}>"
            if tok not in self._vocab:
                tok = "<unk>"
            ids.append(self._vocab[tok])
            tokens.append(tok)
        return TokenizerResult(ids=ids, tokens=tokens)

    def decode(self, ids: list[int]) -> str:
        chars = []
        for i in ids:
            tok = self._inv_vocab.get(i, "<unk>")
            if tok.startswith("<0x") and tok.endswith(">") and len(tok) == 6:
                try:
                    chars.append(chr(int(tok[3:-1], 16)))
                except ValueError:
                    chars.append(tok)
            else:
                chars.append(tok)
        return "".join(chars)

    def vocab_size(self) -> int:
        return len(self._vocab)

    def get_vocab(self) -> dict[str, int]:
        return dict(self._vocab)

    def save(self, directory: str) -> None:
        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, "vocab.json"), "w", encoding="utf-8") as f:
            json.dump(self._vocab, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, directory: str) -> ByteTokenizer:
        with open(os.path.join(directory, "vocab.json"), encoding="utf-8") as f:
            vocab = json.load(f)
        tok = cls()
        tok._vocab = vocab
        tok._inv_vocab = {v: k for k, v in vocab.items()}
        return tok


# ---------------------------------------------------------------------------
# 6. Character tokenizer
# ---------------------------------------------------------------------------
class CharacterTokenizer(BaseTokenizer):
    name = "character"

    def __init__(self, special_tokens: list[str] | None = None) -> None:
        self.special_tokens = special_tokens or ["<s>", "<pad>", "</s>", "<unk>"]
        self._vocab: dict[str, int] = {}
        self._inv_vocab: dict[int, str] = {}
        for i, tok in enumerate(self.special_tokens):
            self._vocab[tok] = i
            self._inv_vocab[i] = tok

    def _ensure_char(self, ch: str) -> int:
        if ch not in self._vocab:
            idx = len(self._vocab)
            self._vocab[ch] = idx
            self._inv_vocab[idx] = ch
        return self._vocab[ch]

    def encode(self, text: str) -> TokenizerResult:
        ids: list[int] = []
        tokens: list[str] = []
        for ch in text:
            idx = self._vocab.get(ch, self._vocab.get("<unk>", 3))
            tokens.append(ch)
            ids.append(idx)
        return TokenizerResult(ids=ids, tokens=tokens)

    def decode(self, ids: list[int]) -> str:
        return "".join(self._inv_vocab.get(i, "<unk>") for i in ids)

    def vocab_size(self) -> int:
        return len(self._vocab)

    def get_vocab(self) -> dict[str, int]:
        return dict(self._vocab)

    def save(self, directory: str) -> None:
        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, "vocab.json"), "w", encoding="utf-8") as f:
            json.dump(self._vocab, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, directory: str) -> CharacterTokenizer:
        with open(os.path.join(directory, "vocab.json"), encoding="utf-8") as f:
            vocab = json.load(f)
        tok = cls()
        tok._vocab = vocab
        tok._inv_vocab = {v: k for k, v in vocab.items()}
        return tok


# ---------------------------------------------------------------------------
# 7. Adaptive tokenizer
# ---------------------------------------------------------------------------
class AdaptiveTokenizer(BaseTokenizer):
    name = "adaptive"

    def __init__(self, base_tokenizer: BaseTokenizer, max_vocab_size: int = 100_000) -> None:
        self.base_tokenizer = base_tokenizer
        self.max_vocab_size = max_vocab_size
        self._online_counter: collections.Counter[str] = collections.Counter()
        self._pending_updates: int = 0
        self._update_threshold: int = 1000

    def encode(self, text: str) -> TokenizerResult:
        result = self.base_tokenizer.encode(text)
        self._online_counter.update(result.tokens)
        self._pending_updates += len(result.tokens)
        if self._pending_updates >= self._update_threshold:
            self._apply_online_update()
        return result

    def _apply_online_update(self) -> None:
        self._pending_updates = 0
        current_vocab = self.base_tokenizer.get_vocab()
        new_tokens = [tok for tok, _ in self._online_counter.most_common() if tok not in current_vocab]
        if not new_tokens:
            return
        overflow = len(current_vocab) + len(new_tokens) - self.max_vocab_size
        if overflow > 0:
            freq = collections.Counter({tok: self._online_counter[tok] for tok in new_tokens})
            candidates = [tok for tok, _ in freq.most_common()[:-overflow]]
            new_tokens = candidates if candidates else new_tokens[: max(0, len(new_tokens) - overflow)]
        if new_tokens:
            self._merge_vocab_tokens(new_tokens[: max(0, self.max_vocab_size - len(current_vocab))])
        self._online_counter.clear()

    def _merge_vocab_tokens(self, tokens: list[str]) -> None:
        vocab = self.base_tokenizer.get_vocab()
        next_id = max(vocab.values(), default=-1) + 1
        for tok in tokens:
            if tok not in vocab:
                vocab[tok] = next_id
                next_id += 1
        if hasattr(self.base_tokenizer, "_vocab"):
            self.base_tokenizer._vocab = vocab  # type: ignore[attr-defined]

    def decode(self, ids: list[int]) -> str:
        return self.base_tokenizer.decode(ids)

    def vocab_size(self) -> int:
        return self.base_tokenizer.vocab_size()

    def get_vocab(self) -> dict[str, int]:
        return self.base_tokenizer.get_vocab()

    def save(self, directory: str) -> None:
        os.makedirs(directory, exist_ok=True)
        self.base_tokenizer.save(directory)
        meta = {
            "max_vocab_size": self.max_vocab_size,
            "pending_updates": self._pending_updates,
            "update_threshold": self._update_threshold,
        }
        with open(os.path.join(directory, "adaptive_meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

    @classmethod
    def load(cls, directory: str, base_tokenizer_cls: type[BaseTokenizer]) -> AdaptiveTokenizer:
        base = base_tokenizer_cls.load(directory)
        meta_path = os.path.join(directory, "adaptive_meta.json")
        meta = {}
        if os.path.exists(meta_path):
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)
        instance = cls(base_tokenizer=base, max_vocab_size=meta.get("max_vocab_size", 100_000))
        instance._pending_updates = meta.get("pending_updates", 0)
        instance._update_threshold = meta.get("update_threshold", 1000)
        return instance


# ---------------------------------------------------------------------------
# 8. Dynamic vocabulary
# ---------------------------------------------------------------------------
class DynamicVocabulary:
    """Mutable vocabulary container backed by LRU eviction."""

    def __init__(self, max_size: int = 50_000) -> None:
        self.max_size = max_size
        self._token_to_id: dict[str, int] = {}
        self._id_to_token: dict[int, str] = {}
        self._access_count: dict[str, int] = {}
        self._next_id: int = 0

    def add(self, token: str) -> int:
        if token in self._token_to_id:
            self._access_count[token] = self._access_count.get(token, 0) + 1
            return self._token_to_id[token]
        if len(self._token_to_id) >= self.max_size:
            self._evict()
        idx = self._next_id
        self._next_id += 1
        self._token_to_id[token] = idx
        self._id_to_token[idx] = token
        self._access_count[token] = 1
        return idx

    def add_many(self, tokens: Iterable[str]) -> None:
        for tok in tokens:
            self.add(tok)

    def _evict(self) -> None:
        if not self._token_to_id:
            return
        lru_token = min(self._access_count.items(), key=lambda item: item[1])[0]
        rid = self._token_to_id.pop(lru_token)
        self._id_to_token.pop(rid, None)
        self._access_count.pop(lru_token, None)

    def prune_by_frequency(self, corpus_tokens: list[str], min_count: int = 2) -> int:
        freq: collections.Counter[str] = collections.Counter(corpus_tokens)
        to_remove = [tok for tok in self._token_to_id if freq.get(tok, 0) < min_count]
        removed = 0
        for tok in to_remove:
            if tok in self._token_to_id:
                rid = self._token_to_id.pop(tok)
                self._id_to_token.pop(rid, None)
                self._access_count.pop(tok, None)
                removed += 1
        if removed:
            self._next_id = max(self._id_to_token.keys(), default=-1) + 1
        return removed

    def merge(self, other: DynamicVocabulary, overlap_strategy: str = "keep") -> DynamicVocabulary:
        merged = DynamicVocabulary(max_size=max(self.max_size, other.max_size))
        for tok, idx in self._token_to_id.items():
            merged._token_to_id[tok] = idx
            merged._id_to_token[idx] = tok
            merged._access_count[tok] = self._access_count.get(tok, 0)
        for tok, _idx in other._token_to_id.items():
            if tok in merged._token_to_id:
                if overlap_strategy == "keep":
                    continue
                if overlap_strategy == "sum":
                    merged._access_count[tok] = (
                        merged._access_count.get(tok, 0) + other._access_count.get(tok, 0)
                    )
                    continue
                if overlap_strategy == "replace":
                    pass
            new_idx = len(merged._token_to_id)
            merged._token_to_id[tok] = new_idx
            merged._id_to_token[new_idx] = tok
            merged._access_count[tok] = other._access_count.get(tok, 0)
        merged._next_id = len(merged._token_to_id)
        return merged

    def save(self, directory: str) -> None:
        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, "dynamic_vocab.json"), "w", encoding="utf-8") as f:
            json.dump(
                {
                    "token_to_id": self._token_to_id,
                    "max_size": self.max_size,
                    "next_id": self._next_id,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

    @classmethod
    def load(cls, directory: str) -> DynamicVocabulary:
        path = os.path.join(directory, "dynamic_vocab.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        vocab = cls(max_size=data.get("max_size", 50_000))
        vocab._token_to_id = data.get("token_to_id", {})
        vocab._id_to_token = {v: k for k, v in vocab._token_to_id.items()}
        vocab._next_id = data.get("next_id", len(vocab._token_to_id))
        vocab._access_count = dict.fromkeys(vocab._token_to_id, 1)
        return vocab


# ---------------------------------------------------------------------------
# 9. Online tokenizer update
# ---------------------------------------------------------------------------
class OnlineTokenizerUpdater:
    """Applies incremental vocabulary updates to a base tokenizer."""

    def __init__(self, tokenizer: BaseTokenizer, buffer_size: int = 10_000) -> None:
        self.tokenizer = tokenizer
        self.buffer_size = buffer_size
        self._buffer: list[str] = []
        self._token_counter: collections.Counter[str] = collections.Counter()

    def ingest(self, text: str) -> None:
        result = self.tokenizer.encode(text)
        tokens = result.tokens
        self._buffer.extend(tokens)
        self._token_counter.update(tokens)
        if len(self._buffer) >= self.buffer_size:
            self.flush()

    def flush(self) -> int:
        added = 0
        current_vocab = self.tokenizer.get_vocab()
        vocab_size = self.tokenizer.vocab_size()
        if vocab_size >= 200_000:
            return added
        for tok, _ in self._token_counter.most_common():
            if tok not in current_vocab:
                current_vocab[tok] = len(current_vocab)
                added += 1
                if len(current_vocab) >= 200_000:
                    break
        self._buffer.clear()
        self._token_counter.clear()
        if hasattr(self.tokenizer, "_vocab"):
            self.tokenizer._vocab = current_vocab  # type: ignore[attr-defined]
        if hasattr(self.tokenizer, "_build_hf_tokenizer"):
            with contextlib.suppress(Exception):
                self.tokenizer._build_hf_tokenizer()  # type: ignore[attr-defined]
        return added


# ---------------------------------------------------------------------------
# 10. Vocabulary pruning
# ---------------------------------------------------------------------------
class VocabularyPruner:
    @staticmethod
    def prune(
        tokenizer: BaseTokenizer,
        corpus_tokens: list[str],
        min_count: int = 2,
        keep_specials: bool = True,
    ) -> tuple[dict[str, int], int]:
        freq = collections.Counter(corpus_tokens)
        new_vocab: dict[str, int] = {}
        removed = 0
        specials = set(tokenizer.special_tokens) if keep_specials and hasattr(tokenizer, "special_tokens") else set()
        for tok, count in freq.items():
            if tok in specials or count >= min_count:
                new_vocab[tok] = len(new_vocab)
            else:
                removed += 1
        return new_vocab, removed

    @staticmethod
    def prune_by_compression_ratio(
        tokenizer: BaseTokenizer,
        texts: list[str],
        ratio_threshold: float = 1.2,
    ) -> tuple[dict[str, int], list[str]]:
        ratios: dict[str, list[float]] = collections.defaultdict(list)
        for text in texts:
            result = tokenizer.encode(text)
            for tok in result.tokens:
                ratios[tok].append(len(tok))
        avg_len: dict[str, float] = {tok: statistics.mean(v) for tok, v in ratios.items()}
        tokens_per_instance: dict[str, list[float]] = collections.defaultdict(list)
        for text in texts:
            result = tokenizer.encode(text)
            tokens_per_instance["_total"].append(len(result.tokens))
            for tok in result.tokens:
                tokens_per_instance[tok].append(1)
        token_freq: dict[str, float] = {}
        total = sum(tokens_per_instance.get("_total", [0]))
        for tok in list(avg_len.keys()):
            token_freq[tok] = sum(tokens_per_instance.get(tok, [])) / total if total else 0.0
        new_vocab: dict[str, int] = {}
        removed: list[str] = []
        for tok, avg in avg_len.items():
            eff = avg / (token_freq.get(tok, 1e-9) * 100.0 + 1e-9)
            if eff >= ratio_threshold or tok in getattr(tokenizer, "special_tokens", []):
                new_vocab[tok] = len(new_vocab)
            else:
                removed.append(tok)
        return new_vocab, removed


# ---------------------------------------------------------------------------
# 11. Vocabulary merging
# ---------------------------------------------------------------------------
class VocabularyMerger:
    @staticmethod
    def merge(
        source: dict[str, int],
        target: dict[str, int],
        strategy: str = "keep",
        reindex: bool = True,
    ) -> dict[str, int]:
        merged: dict[str, int] = {}
        if strategy == "keep":
            merged.update(source)
            for tok, _idx in target.items():
                if tok not in merged:
                    merged[tok] = len(merged)
        elif strategy == "replace":
            merged.update(target)
            for tok, _idx in source.items():
                if tok not in merged:
                    merged[tok] = len(merged)
        elif strategy == "sum":
            all_tokens = set(source) | set(target)
            merged = {tok: i for i, tok in enumerate(all_tokens)}
        elif strategy == "intersect":
            common = set(source) & set(target)
            merged = {tok: i for i, tok in enumerate(common)}
        else:
            raise ValueError(f"Unknown merge strategy: {strategy}")
        if reindex:
            merged = {tok: i for i, tok in enumerate(merged)}
        return merged


# ---------------------------------------------------------------------------
# 12. Compression analysis
# ---------------------------------------------------------------------------
class CompressionAnalyzer:
    @staticmethod
    def analyze(tokenizer: BaseTokenizer, texts: list[str]) -> dict[str, Any]:
        total_chars = 0
        total_tokens = 0
        total_bytes = 0
        token_lengths: list[int] = []
        for text in texts:
            result = tokenizer.encode(text)
            total_chars += len(text)
            total_tokens += len(result.tokens)
            total_bytes += len(text.encode("utf-8"))
            token_lengths.extend(len(tok) for tok in result.tokens)
        return {
            "total_chars": total_chars,
            "total_tokens": total_tokens,
            "total_bytes": total_bytes,
            "chars_per_token": total_chars / total_tokens if total_tokens else 0,
            "bytes_per_token": total_bytes / total_tokens if total_tokens else 0,
            "compression_ratio": total_bytes / total_tokens if total_tokens else 0,
            "avg_token_length": statistics.mean(token_lengths) if token_lengths else 0,
            "median_token_length": statistics.median(token_lengths) if token_lengths else 0,
            "token_length_std": statistics.pstdev(token_lengths) if token_lengths else 0,
        }


# ---------------------------------------------------------------------------
# 13. OOV analysis
# ---------------------------------------------------------------------------
class OOVAnalyzer:
    @staticmethod
    def analyze(
        tokenizer: BaseTokenizer,
        texts: list[str],
        reference_vocab: set[str] | None = None,
    ) -> dict[str, Any]:
        vocab = set(tokenizer.get_vocab().keys())
        reference = reference_vocab or vocab
        oov_tokens: collections.Counter[str] = collections.Counter()
        total_tokens = 0
        for text in texts:
            result = tokenizer.encode(text)
            for tok in result.tokens:
                total_tokens += 1
                if tok not in reference:
                    oov_tokens[tok] += 1
        oov_count = sum(oov_tokens.values())
        return {
            "total_tokens": total_tokens,
            "oov_count": oov_count,
            "oov_rate": oov_count / total_tokens if total_tokens else 0,
            "unique_oov": len(oov_tokens),
            "top_oov": oov_tokens.most_common(20),
        }


# ---------------------------------------------------------------------------
# 14-18. Benchmark suites
# ---------------------------------------------------------------------------
class SpeedBenchmark:
    @staticmethod
    def run(tokenizer: BaseTokenizer, texts: list[str], warmup: int = 10) -> BenchmarkResult:
        for _ in range(warmup):
            tokenizer.encode("warmup text")
        samples: list[BenchmarkSample] = []
        for text in texts:
            result, elapsed_ms = tokenizer._time_encode(text)
            samples.append(
                BenchmarkSample(
                    text=text,
                    encoding_time_ms=elapsed_ms,
                    num_tokens=len(result.ids),
                    num_chars=len(text),
                    num_bytes=len(text.encode("utf-8")),
                    tokens=result.tokens,
                )
            )
        return BenchmarkResult(name=tokenizer.name, samples=samples, metadata={"benchmark": "speed"})


class ContextUtilizationBenchmark:
    @staticmethod
    def run(
        tokenizer: BaseTokenizer,
        texts: list[str],
        context_length: int = 2048,
    ) -> BenchmarkResult:
        samples: list[BenchmarkSample] = []
        for text in texts:
            result, elapsed_ms = tokenizer._time_encode(text)
            num_tokens = len(result.ids)
            samples.append(
                BenchmarkSample(
                    text=text,
                    encoding_time_ms=elapsed_ms,
                    num_tokens=num_tokens,
                    num_chars=len(text),
                    num_bytes=len(text.encode("utf-8")),
                    tokens=result.tokens,
                )
            )
        utilizations = [len(s.tokens) / context_length for s in samples]
        return BenchmarkResult(
            name=f"{tokenizer.name}_context",
            samples=samples,
            metadata={
                "benchmark": "context_utilization",
                "context_length": context_length,
                "avg_utilization": statistics.mean(utilizations) if utilizations else 0,
                "max_utilization": max(utilizations) if utilizations else 0,
            },
        )


class CrossLanguageBenchmark:
    @staticmethod
    def run(
        tokenizer: BaseTokenizer,
        samples: dict[str, list[str]],
    ) -> BenchmarkResult:
        all_samples: list[BenchmarkSample] = []
        for _lang, texts in samples.items():
            for text in texts:
                result, elapsed_ms = tokenizer._time_encode(text)
                all_samples.append(
                    BenchmarkSample(
                        text=text,
                        encoding_time_ms=elapsed_ms,
                        num_tokens=len(result.ids),
                        num_chars=len(text),
                        num_bytes=len(text.encode("utf-8")),
                        tokens=result.tokens,
                    )
                )
        return BenchmarkResult(
            name=f"{tokenizer.name}_cross_lang",
            samples=all_samples,
            metadata={"benchmark": "cross_language", "languages": list(samples.keys())},
        )


class TokenEfficiencyBenchmark:
    @staticmethod
    def run(tokenizer: BaseTokenizer, texts: list[str]) -> BenchmarkResult:
        samples: list[BenchmarkSample] = []
        for text in texts:
            result, elapsed_ms = tokenizer._time_encode(text)
            samples.append(
                BenchmarkSample(
                    text=text,
                    encoding_time_ms=elapsed_ms,
                    num_tokens=len(result.ids),
                    num_chars=len(text),
                    num_bytes=len(text.encode("utf-8")),
                    tokens=result.tokens,
                )
            )
        return BenchmarkResult(
            name=f"{tokenizer.name}_efficiency",
            samples=samples,
            metadata={"benchmark": "token_efficiency"},
        )


# ---------------------------------------------------------------------------
# Training helpers
# ---------------------------------------------------------------------------
def train_bpe_tokenizer(
    texts: list[str],
    vocab_size: int = 50257,
    min_frequency: int = 2,
    special_tokens: list[str] | None = None,
) -> BPETokenizer:
    if not _TOKENIZERS_AVAILABLE:
        raise RuntimeError("huggingface tokenizers package is required for training.")
    special_tokens = special_tokens or ["<s>", "<pad>", "</s>", "<unk>"]
    hf = HFTokenizer(BPE(unk_token="<unk>"))
    hf.pre_tokenizer = ByteLevel()
    trainer = BpeTrainer(
        vocab_size=vocab_size,
        min_frequency=min_frequency,
        special_tokens=special_tokens,
    )
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("\n".join(texts))
        tmp_path = f.name
    try:

        hf.train_from_iterator([tmp_path], trainer=trainer)
    except TypeError:
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f2:
            json.dump(texts, f2)
            tmp_json = f2.name
        hf.train([tmp_json], trainer=trainer)
        os.remove(tmp_json)
    vocab = hf.model.get_vocab()
    merges = list(hf.model.merges.items())
    return BPETokenizer(vocab=vocab, merges=merges, special_tokens=special_tokens)


def train_wordpiece_tokenizer(
    texts: list[str],
    vocab_size: int = 30000,
    min_frequency: int = 2,
    special_tokens: list[str] | None = None,
) -> WordPieceTokenizer:
    if not _TOKENIZERS_AVAILABLE:
        raise RuntimeError("huggingface tokenizers package is required for training.")
    special_tokens = special_tokens or ["[UNK]", "[CLS]", "[SEP]", "[PAD]", "[MASK]"]
    hf = HFTokenizer(WordPiece(unk_token="[UNK]"))
    hf.pre_tokenizer = Whitespace()
    trainer = WordPieceTrainer(
        vocab_size=vocab_size,
        min_frequency=min_frequency,
        special_tokens=special_tokens,
    )
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("\n".join(texts))
        tmp_path = f.name
    try:
        hf.train_from_iterator([tmp_path], trainer=trainer)
    except TypeError:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f2:
            json.dump(texts, f2)
            tmp_json = f2.name
        hf.train([tmp_json], trainer=trainer)
        os.remove(tmp_json)
    vocab = hf.model.get_vocab()
    return WordPieceTokenizer(vocab=vocab, special_tokens=special_tokens)


def train_sentencepiece_model(
    texts: list[str],
    model_prefix: str,
    vocab_size: int = 32000,
    model_type: str = "bpe",
) -> SentencePieceTokenizer:
    if not _SENTENCEPIECE_AVAILABLE:
        raise RuntimeError("sentencepiece is required for training.")
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("\n".join(texts))
        tmp_path = f.name
    try:
        spm.SentencePieceTrainer.train(
            input=tmp_path,
            model_prefix=model_prefix,
            vocab_size=vocab_size,
            model_type=model_type,
            pad_id=0,
            unk_id=1,
            bos_id=2,
            eos_id=3,
            character_coverage=0.9995,
        )
    finally:
        os.remove(tmp_path)
    return SentencePieceTokenizer(model_path=f"{model_prefix}.model")


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------
def generate_comparison_markdown(results: list[BenchmarkResult]) -> str:
    lines = ["# Tokenizer Benchmark Comparison", ""]
    lines.append("| Tokenizer | Texts | Tokens | Chars | Bytes | tok/char | tok/byte | tok/s |")
    lines.append("|-----------|------:|-------:|------:|------:|---------:|---------:|------:|")
    for r in results:
        lines.append(
            f"| {r.name} | {r.total_texts} | {r.total_tokens} | {r.total_chars} | "
            f"{r.total_bytes} | {r.avg_tokens_per_char:.4f} | {r.avg_tokens_per_byte:.4f} | "
            f"{r.tokens_per_second:.2f} |"
        )
    lines.extend(["", "## Detailed Metrics", ""])
    for r in results:
        lines.append(f"### {r.name}")
        for k, v in r.to_dict().items():
            if k not in {"name", "metadata"}:
                lines.append(f"- **{k}:** {v}")
        lines.append("")
    return "\n".join(lines) + "\n"
