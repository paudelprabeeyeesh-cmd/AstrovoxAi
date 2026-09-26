"""BPE (Byte Pair Encoding) trainer for tokenization."""

from __future__ import annotations

import json
import logging
import os
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class BPETrainerConfig:
    vocab_size: int = 32000
    min_frequency: int = 2
    special_tokens: List[str] = field(default_factory=lambda: ["<unk>", "<pad>", "<s>", "</s>"])
    lowercase: bool = False
    normalization_form: str = "NFKC"


class BPETrainer:
    def __init__(self, config: Optional[BPETrainerConfig] = None):
        self.config = config or BPETrainerConfig()
        self.vocab: Dict[str, int] = {}
        self.inverse_vocab: Dict[int, str] = {}
        self.merges: List[Tuple[str, str]] = []
        self._word_freqs: Counter = Counter()

    @property
    def vocab_size(self) -> int:
        return len(self.vocab)

    def _pre_tokenize(self, text: str) -> List[str]:
        import unicodedata

        text = unicodedata.normalize(self.config.normalization_form, text)
        if self.config.lowercase:
            text = text.lower()
        return text.split()

    def _get_stats(self, words: List[List[str]]) -> Counter:
        pairs = Counter()
        for word in words:
            for i in range(len(word) - 1):
                pairs[(word[i], word[i + 1])] += 1
        return pairs

    def _merge_vocab(self, pair: Tuple[str, str], words: List[List[str]]) -> List[List[str]]:
        bigram = " ".join(pair)
        replacement = "".join(pair)
        v_out = []
        for word in words:
            new_word = []
            i = 0
            while i < len(word):
                if i < len(word) - 1 and word[i] == pair[0] and word[i + 1] == pair[1]:
                    new_word.append(replacement)
                    i += 2
                else:
                    new_word.append(word[i])
                    i += 1
            v_out.append(new_word)
        return v_out

    def train(self, corpus: List[str]) -> None:
        self._word_freqs = Counter()
        for text in corpus:
            for token in self._pre_tokenize(text):
                self._word_freqs[token] += 1

        words = [[char for char in word] for word in self._word_freqs]
        self.vocab = {token: idx for idx, token in enumerate(self.config.special_tokens)}
        idx = len(self.vocab)
        unique_chars = sorted({char for word in words for char in word})
        for char in unique_chars:
            if char not in self.vocab:
                self.vocab[char] = idx
                idx += 1

        self.merges = []
        for _ in range(self.config.vocab_size - len(self.vocab)):
            pairs = self._get_stats(words)
            if not pairs:
                break
            best_pair, best_freq = pairs.most_common(1)[0]
            if best_freq < self.config.min_frequency:
                break
            self.merges.append(best_pair)
            words = self._merge_vocab(best_pair, words)
            merged_token = "".join(best_pair)
            if merged_token not in self.vocab:
                self.vocab[merged_token] = idx
                idx += 1

        self.inverse_vocab = {idx: token for token, idx in self.vocab.items()}
        logger.info("BPE training complete: vocab_size=%d, num_merges=%d", self.vocab_size, len(self.merges))

    def encode(self, text: str) -> List[int]:
        tokens: List[int] = []
        for token in self._pre_tokenize(text):
            word = list(token)
            for pair in self.merges:
                new_word: List[str] = []
                i = 0
                while i < len(word):
                    if i < len(word) - 1 and word[i] == pair[0] and word[i + 1] == pair[1]:
                        new_word.append("".join(pair))
                        i += 2
                    else:
                        new_word.append(word[i])
                        i += 1
                word = new_word
            for sub in word:
                tokens.append(self.vocab.get(sub, self.vocab.get("<unk>", 0)))
        return tokens

    def decode(self, ids: List[int]) -> str:
        return "".join(self.inverse_vocab.get(i, "<unk>") for i in ids)

    def save(self, path: str) -> None:
        data = {
            "vocab": self.vocab,
            "merges": self.merges,
            "config": {
                "vocab_size": self.config.vocab_size,
                "min_frequency": self.config.min_frequency,
                "special_tokens": self.config.special_tokens,
                "lowercase": self.config.lowercase,
                "normalization_form": self.config.normalization_form,
            },
        }
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("BPE model saved to %s", path)

    def load(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.vocab = {k: int(v) for k, v in data["vocab"].items()}
        self.inverse_vocab = {int(v): k for k, v in self.vocab.items()}
        self.merges = [tuple(m) for m in data["merges"]]
        cfg = data.get("config", {})
        self.config = BPETrainerConfig(**cfg)
        logger.info("BPE model loaded from %s", path)

    def add_tokens(self, tokens: List[str], min_frequency: int = 2) -> None:
        counts = Counter(tokens)
        added = 0
        for token, freq in counts.items():
            if freq >= min_frequency and token not in self.vocab:
                self.vocab[token] = len(self.vocab)
                self.inverse_vocab[len(self.inverse_vocab)] = token
                added += 1
        logger.info("Added %d new tokens to BPE vocab", added)
