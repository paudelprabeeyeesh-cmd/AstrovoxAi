"""Dynamic vocabulary expansion for streaming tokenization."""

from __future__ import annotations

import logging
import threading
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class DynamicVocabularyConfig:
    max_vocab_size: int = 100000
    min_frequency: int = 2
    update_interval: int = 1000
    reserved_tokens: List[str] = field(default_factory=lambda: ["<unk>", "<pad>", "<s>", "</s>"])


class DynamicVocabulary:
    def __init__(self, config: Optional[DynamicVocabularyConfig] = None):
        self.config = config or DynamicVocabularyConfig()
        self.token_counts: Counter = Counter()
        self.vocab: Dict[str, int] = {}
        self.inverse_vocab: Dict[int, str] = {}
        self._lock = threading.Lock()
        self._updates_since_rebuild: int = 0
        self._initialize_reserved()

    def _initialize_reserved(self) -> None:
        self.vocab = {token: idx for idx, token in enumerate(self.config.reserved_tokens)}
        self.inverse_vocab = {idx: token for token, idx in self.vocab.items()}

    def add_tokens(self, tokens: List[str]) -> None:
        with self._lock:
            self.token_counts.update(tokens)
            self._updates_since_rebuild += len(tokens)
            if self._updates_since_rebuild >= self.config.update_interval:
                self._rebuild()
                self._updates_since_rebuild = 0

    def add_text(self, text: str) -> None:
        self.add_tokens(text.split())

    def _rebuild(self) -> None:
        sorted_tokens = self.token_counts.most_common()
        available = self.config.max_vocab_size - len(self.config.reserved_tokens)
        selected = [token for token, _ in sorted_tokens if token not in self.vocab and _ >= self.config.min_frequency]
        idx = len(self.vocab)
        for token in selected[:available]:
            if idx >= self.config.max_vocab_size:
                break
            self.vocab[token] = idx
            self.inverse_vocab[idx] = token
            idx += 1
        logger.debug("Dynamic vocabulary rebuilt: size=%d", len(self.vocab))

    def encode(self, text: str) -> List[int]:
        unk = self.vocab.get("<unk>", 0)
        return [self.vocab.get(token, unk) for token in text.split()]

    def decode(self, ids: List[int]) -> str:
        return " ".join(self.inverse_vocab.get(i, "<unk>") for i in ids)

    def expand(self, new_tokens: List[str]) -> int:
        with self._lock:
            added = 0
            for token in new_tokens:
                if token not in self.vocab and len(self.vocab) < self.config.max_vocab_size:
                    self.vocab[token] = len(self.vocab)
                    self.inverse_vocab[len(self.inverse_vocab)] = token
                    added += 1
            logger.info("Expanded vocabulary by %d tokens", added)
            return added

    def prune(self, min_frequency: Optional[int] = None) -> int:
        threshold = min_frequency or self.config.min_frequency
        to_remove = [token for token, idx in self.vocab.items() if self.token_counts.get(token, 0) < threshold and token not in self.config.reserved_tokens]
        for token in to_remove:
            idx = self.vocab.pop(token)
            self.inverse_vocab.pop(idx, None)
        self._rebuild()
        logger.info("Pruned %d low-frequency tokens", len(to_remove))
        return len(to_remove)

    def size(self) -> int:
        return len(self.vocab)

    def get_token_frequency(self, token: str) -> int:
        return self.token_counts.get(token, 0)
