"""BPE trainer for ASTROVOX_AI ai_core."""

from __future__ import annotations

import logging
from collections import Counter
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class BPETrainer:
    def __init__(self, vocab_size: int = 50257, min_frequency: int = 2, special_tokens: Optional[List[str]] = None):
        self.vocab_size = vocab_size
        self.min_frequency = min_frequency
        self.special_tokens = special_tokens or ["<unk>", "<pad>", "<s>", "</s>"]
        self.merges: List[Tuple[str, str]] = []
        self.vocab: Dict[str, int] = {}
        self.inverse_vocab: Dict[int, str] = {}

    def get_stats(self, words: List[List[str]]) -> Counter:
        pairs = Counter()
        for word in words:
            for i in range(len(word) - 1):
                pairs[(word[i], word[i + 1])] += 1
        return pairs

    def merge_vocab(self, pair: Tuple[str, str], v_in: List[List[str]]) -> List[List[str]]:
        v_out = []
        bigram = " ".join(pair)
        replacement = "".join(pair)
        for word in v_in:
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
        words = [list(word) for text in corpus for word in text.split()]
        self.vocab = {token: idx for idx, token in enumerate(self.special_tokens)}
        idx = len(self.vocab)
        unique_chars = sorted({char for word in words for char in word})
        for char in unique_chars:
            if char not in self.vocab:
                self.vocab[char] = idx
                idx += 1
        for _ in range(self.vocab_size - len(self.vocab)):
            pairs = self.get_stats(words)
            if not pairs:
                break
            best_pair = max(pairs, key=pairs.get)
            if pairs[best_pair] < self.min_frequency:
                break
            self.merges.append(best_pair)
            words = self.merge_vocab(best_pair, words)
            merged = "".join(best_pair)
            if merged not in self.vocab:
                self.vocab[merged] = idx
                idx += 1
        self.inverse_vocab = {v: k for k, v in self.vocab.items()}
        logger.info("BPETrainer trained: vocab_size=%d, merges=%d", len(self.vocab), len(self.merges))

    def encode(self, text: str) -> List[int]:
        word = list(text)
        for pair in self.merges:
            word = self._merge(word, pair)
        return [self.vocab.get(token, self.vocab.get("<unk>", 0)) for token in word]

    def _merge(self, word: List[str], pair: Tuple[str, str]) -> List[str]:
        new_word = []
        i = 0
        while i < len(word):
            if i < len(word) - 1 and word[i] == pair[0] and word[i + 1] == pair[1]:
                new_word.append(pair[0] + pair[1])
                i += 2
            else:
                new_word.append(word[i])
                i += 1
        return new_word

    def decode(self, ids: List[int]) -> str:
        return "".join(self.inverse_vocab.get(i, "<unk>") for i in ids)

    def save(self, path: str) -> None:
        import json
        import os

        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"vocab": self.vocab, "merges": self.merges, "inverse_vocab": self.inverse_vocab}, f, ensure_ascii=False, indent=2)

    def load(self, path: str) -> None:
        import json

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.vocab = {k: int(v) for k, v in data["vocab"].items()}
        self.merges = [tuple(m) for m in data["merges"]]
        self.inverse_vocab = {int(k): v for k, v in data.get("inverse_vocab", {}).items()}

    def add_tokens(self, tokens: List[str], min_frequency: int = 2) -> None:
        counts = Counter(tokens)
        for token, freq in counts.items():
            if freq >= min_frequency and token not in self.vocab:
                self.vocab[token] = len(self.vocab)
                self.inverse_vocab[len(self.inverse_vocab)] = token
