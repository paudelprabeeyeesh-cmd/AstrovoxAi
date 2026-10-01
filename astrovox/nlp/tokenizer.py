"""Tokenizers for character and word-level language modelling.

Both are deterministic and dependency-free, which is what an example and a
test need. A byte-level vocabulary of 256 plus a few special tokens covers any
UTF-8 input without an unknown token, so a character model can never lose
information.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

PAD = "<pad>"
BOS = "<bos>"
EOS = "<eos>"
UNK = "<unk>"
SPECIALS = (PAD, BOS, EOS, UNK)


@dataclass
class Encoding:
    """One encoded sequence."""

    ids: list[int]
    attention_mask: list[int]

    def __len__(self) -> int:
        return len(self.ids)


class Tokenizer:
    """Base class defining the tokenizer contract."""

    vocab_size: int
    pad_id: int
    bos_id: int
    eos_id: int
    unk_id: int

    def encode(self, text: str) -> list[int]:
        """Return the token ids for ``text``."""
        raise NotImplementedError

    def decode(self, ids: Sequence[int], skip_specials: bool = True) -> str:
        """Return the text for ``ids``."""
        raise NotImplementedError

    def encode_batch(
        self, texts: Sequence[str], max_length: int | None = None, padding: bool = True
    ) -> tuple[np.ndarray, np.ndarray]:
        """Encode several texts, returning ids and an attention mask.

        Longer sequences are truncated and shorter ones padded, so a batch is
        rectangular and a loss over it is well defined.
        """
        sequences = [self.encode(text) for text in texts]
        if max_length is not None:
            sequences = [seq[:max_length] for seq in sequences]
        if padding:
            width = max((len(seq) for seq in sequences), default=0)
            if max_length is not None:
                width = max(width, max_length)
        else:
            width = max((len(seq) for seq in sequences), default=0)
        ids = np.full((len(sequences), width), self.pad_id, dtype=np.int64)
        mask = np.zeros((len(sequences), width), dtype=np.int64)
        for row, seq in enumerate(sequences):
            ids[row, : len(seq)] = seq
            mask[row, : len(seq)] = 1
        return ids, mask

    def save(self, path: str | Path) -> Path:
        """Write the tokenizer vocabulary to disk."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({"vocab": list(self.vocab), "kind": self.kind}), encoding="utf-8")
        return target

    @classmethod
    def load(cls, path: str | Path) -> "Tokenizer":
        """Read a tokenizer written by :meth:`save`."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("kind") == "char":
            return CharTokenizer.from_vocab(data["vocab"])
        if data.get("kind") == "word":
            return WordTokenizer.from_vocab(data["vocab"])
        raise ValueError(f"Unknown tokenizer kind: {data.get('kind')!r}")


class CharTokenizer(Tokenizer):
    """A byte-level tokenizer: every byte is one token.

    The vocabulary covers all 256 byte values, so any input is encodable and
    there is no unknown token in practice. Covering the control characters
    too matters: text containing a tab or newline would otherwise be silently
    replaced.
    """

    kind = "char"

    def __init__(self) -> None:
        self.itos: list[str] = list(SPECIALS) + [chr(c) for c in range(256)]
        self.stoi: dict[str, int] = {token: i for i, token in enumerate(self.itos)}
        self.vocab = self.itos
        self.vocab_size = len(self.itos)
        self.pad_id = self.stoi[PAD]
        self.bos_id = self.stoi[BOS]
        self.eos_id = self.stoi[EOS]
        self.unk_id = self.stoi[UNK]

    @classmethod
    def from_vocab(cls, vocab: Sequence[str]) -> "CharTokenizer":
        """Rebuild a tokenizer from a stored vocabulary, without re-deriving it."""
        tokenizer = cls.__new__(cls)
        tokenizer.itos = list(vocab)
        tokenizer.stoi = {token: i for i, token in enumerate(tokenizer.itos)}
        tokenizer.vocab = tokenizer.itos
        tokenizer.vocab_size = len(tokenizer.itos)
        tokenizer.pad_id = tokenizer.stoi[PAD]
        tokenizer.bos_id = tokenizer.stoi[BOS]
        tokenizer.eos_id = tokenizer.stoi[EOS]
        tokenizer.unk_id = tokenizer.stoi[UNK]
        return tokenizer

    def encode(self, text: str) -> list[int]:
        """Return one id per byte of ``text``."""
        raw = text.encode("utf-8", errors="replace")
        return [self.stoi.get(chr(b), self.unk_id) for b in raw]

    def decode(self, ids: Sequence[int], skip_specials: bool = True) -> str:
        """Return the text for ``ids``.

        Byte tokens are reassembled in order and decoded as UTF-8. With
        ``skip_specials=False`` the special tokens appear as their own text
        rather than being dropped.
        """
        pieces: list[str] = []
        raw = bytearray()
        for token_id in ids:
            if token_id < 0 or token_id >= len(self.itos):
                continue
            token = self.itos[token_id]
            if token in SPECIALS:
                if skip_specials:
                    continue
                pieces.append(token)
                continue
            raw.extend(token.encode("utf-8", errors="ignore"))
        body = raw.decode("utf-8", errors="ignore")
        return f"{pieces[0]}{body}{''.join(pieces[1:])}" if pieces else body


class WordTokenizer(Tokenizer):
    """A word-level tokenizer with a frequency cutoff."""

    kind = "word"

    def __init__(self, texts: Iterable[str] | None = None, min_frequency: int = 1, max_vocab: int = 20000) -> None:
        counts: Counter[str] = Counter()
        for text in texts or []:
            counts.update(text.lower().split())
        kept = [word for word, count in counts.most_common(max_vocab) if count >= min_frequency]
        self.itos: list[str] = list(SPECIALS) + kept
        self.stoi: dict[str, int] = {token: i for i, token in enumerate(self.itos)}
        self.vocab = self.itos
        self.vocab_size = len(self.itos)
        self.pad_id = self.stoi[PAD]
        self.bos_id = self.stoi[BOS]
        self.eos_id = self.stoi[EOS]
        self.unk_id = self.stoi[UNK]

    @classmethod
    def from_vocab(cls, vocab: Sequence[str]) -> "WordTokenizer":
        """Rebuild a tokenizer from a stored vocabulary, without re-fitting."""
        tokenizer = cls.__new__(cls)
        tokenizer.itos = list(vocab)
        tokenizer.stoi = {token: i for i, token in enumerate(tokenizer.itos)}
        tokenizer.vocab = tokenizer.itos
        tokenizer.vocab_size = len(tokenizer.itos)
        tokenizer.pad_id = tokenizer.stoi[PAD]
        tokenizer.bos_id = tokenizer.stoi[BOS]
        tokenizer.eos_id = tokenizer.stoi[EOS]
        tokenizer.unk_id = tokenizer.stoi[UNK]
        return tokenizer

    def encode(self, text: str) -> list[int]:
        """Return one id per whitespace-separated word."""
        return [self.stoi.get(word, self.unk_id) for word in text.lower().split()]

    def decode(self, ids: Sequence[int], skip_specials: bool = True) -> str:
        """Return the text for ``ids``."""
        words = []
        for token_id in ids:
            if token_id < 0 or token_id >= len(self.itos):
                continue
            token = self.itos[token_id]
            if skip_specials and token in SPECIALS:
                continue
            words.append(token)
        return " ".join(words)


class Dataset:
    """A corpus split into fixed-length token windows.

    Language modelling needs contiguous input and target sequences, where the
    target is the input shifted by one position.
    """

    def __init__(self, ids: Sequence[int], block_size: int) -> None:
        usable = len(ids) - 1
        if usable < block_size:
            raise ValueError(
                f"Corpus of {len(ids)} tokens is too short for block size {block_size}"
            )
        self.ids = np.asarray(ids, dtype=np.int64)
        self.block_size = block_size
        count = usable // block_size
        self.count = max(count, 1)

    def __len__(self) -> int:
        return self.count

    def batch(self, index: int) -> tuple[np.ndarray, np.ndarray]:
        """Return the ``(inputs, targets)`` pair for window ``index``.

        The target is the input shifted left by one, so predicting it means
        predicting the next token.
        """
        start = index * self.block_size
        chunk = self.ids[start : start + self.block_size + 1]
        return chunk[:-1], chunk[1:]

    def epoch(self, batch_size: int) -> list[tuple[np.ndarray, np.ndarray]]:
        """Return one finite pass over every window, as batches.

        Validation wants a fixed set of batches; training wants an endless
        stream. Materialising a pass is what tells the two apart, because a
        generator that "restarts" cannot be counted.
        """
        if self.count == 0:
            return []
        batches = []
        for start in range(0, self.count, batch_size):
            chunk = [self.batch(index) for index in range(start, min(start + batch_size, self.count))]
            if not chunk:
                continue
            batches.append(
                (np.stack([w[0] for w in chunk]), np.stack([w[1] for w in chunk]))
            )
        return batches

    def batches(self, batch_size: int) -> Iterable[tuple[np.ndarray, np.ndarray]]:
        """Yield ``(inputs, targets)`` batches, cycling through the corpus.

        This is infinite: training runs for a configured number of steps,
        which is usually more than there are windows, so nothing stops the
        loop from passing the end of the data. Use :meth:`epoch` when a
        finite pass is wanted.
        """
        if self.count == 0:
            return
        index = 0
        while True:
            chunk = [self.batch((index + offset) % self.count) for offset in range(batch_size)]
            index += batch_size
            yield np.stack([w[0] for w in chunk]), np.stack([w[1] for w in chunk])
