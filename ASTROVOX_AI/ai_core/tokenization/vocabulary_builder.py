"""Vocabulary builder with dynamic expansion and Unicode support."""

from __future__ import annotations

import logging
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class VocabularyBuilderConfig:
    vocab_size: int = 50257
    min_frequency: int = 2
    special_tokens: List[str] = field(default_factory=lambda: ["<unk>", "<pad>", "<s>", "</s>", "<mask>"])
    lowercase: bool = False
    normalization_form: str = "NFKC"
    max_dynamic_expansion: int = 1000


class VocabularyBuilder:
    def __init__(self, config: Optional[VocabularyBuilderConfig] = None):
        self.config = config or VocabularyBuilderConfig()
        self.vocab: Dict[str, int] = {}
        self.inverse_vocab: Dict[int, str] = {}
        self.merges: List[Tuple[str, str]] = []
        self._dynamic_queue: List[str] = []

    def _normalize(self, text: str) -> str:
        text = unicodedata.normalize(self.config.normalization_form, text)
        if self.config.lowercase:
            text = text.lower()
        return text

    def build(self, corpus: List[str]) -> Dict[str, int]:
        normalized = [self._normalize(text) for text in corpus]
        words = [list(word) for text in normalized for word in text.split()]
        self.vocab = {token: idx for idx, token in enumerate(self.config.special_tokens)}
        idx = len(self.vocab)
        unique_chars = sorted({char for word in words for char in word})
        for char in unique_chars:
            if char not in self.vocab:
                self.vocab[char] = idx
                idx += 1
        for _ in range(self.config.vocab_size - len(self.vocab)):
            pairs = self._get_pair_counts(words)
            if not pairs:
                break
            best = max(pairs, key=pairs.get)
            if pairs[best] < self.config.min_frequency:
                break
            self.merges.append(best)
            words = self._merge_vocab(best, words)
            merged = "".join(best)
            if merged not in self.vocab:
                self.vocab[merged] = idx
                idx += 1
        self.inverse_vocab = {v: k for k, v in self.vocab.items()}
        return self.vocab

    def _get_pair_counts(self, words: List[List[str]]) -> Counter:
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

    def _tokenize(self, text: str) -> List[str]:
        tokens = []
        for word in text.split():
            subword = self._encode_word(word)
            tokens.extend(subword)
        return tokens

    def _encode_word(self, word: str) -> List[str]:
        chars = list(word)
        for merge in self.merges:
            new_chars = []
            i = 0
            while i < len(chars):
                if i < len(chars) - 1 and chars[i] == merge[0] and chars[i + 1] == merge[1]:
                    new_chars.append("".join(merge))
                    i += 2
                else:
                    new_chars.append(chars[i])
                    i += 1
            chars = new_chars
        return chars

    def encode(self, text: str) -> List[int]:
        tokens = self._tokenize(self._normalize(text))
        return [self.vocab.get(token, self.vocab.get("<unk>", 0)) for token in tokens]

    def decode(self, ids: List[int]) -> str:
        return "".join(self.inverse_vocab.get(i, "") for i in ids)

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
        self.merges = [tuple(m) for m in data.get("merges", [])]
        self.inverse_vocab = {int(k): v for k, v in data.get("inverse_vocab", {}).items()}

    def expand_dynamic(self, new_texts: List[str]) -> int:
        counts = Counter(self._normalize(t) for text in new_texts for t in text.split())
        added = 0
        for token, freq in counts.most_common():
            if added >= self.config.max_dynamic_expansion:
                break
            if freq >= self.config.min_frequency and token not in self.vocab:
                self.vocab[token] = len(self.vocab)
                self.inverse_vocab[len(self.inverse_vocab)] = token
                added += 1
        logger.info("Vocabulary expanded by %d tokens", added)
        return added

    def get_vocab_size(self) -> int:
        return len(self.vocab)

    def get_special_token_ids(self) -> Dict[str, int]:
        return {token: self.vocab[token] for token in self.config.special_tokens if token in self.vocab}
