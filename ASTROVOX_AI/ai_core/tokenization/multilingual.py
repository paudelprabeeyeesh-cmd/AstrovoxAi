"""Multilingual tokenizer for ASTROVOX_AI."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


_SCRIPT_PATTERNS: Dict[str, str] = {
    "zh": r"[\u4e00-\u9fff]",
    "ja": r"[\u3040-\u309f\u30a0-\u30ff]",
    "ko": r"[\uac00-\ud7af]",
    "ar": r"[\u0600-\u06ff]",
    "hi": r"[\u0900-\u097f]",
    "ru": r"[\u0400-\u04ff]",
    "th": r"[\u0e00-\u0e7f]",
    "el": r"[\u0370-\u03ff]",
    "he": r"[\u0590-\u05ff]",
}


@dataclass
class MultilingualConfig:
    vocab_size: int = 100000
    languages: List[str] = field(default_factory=lambda: ["en", "es", "fr", "de", "zh", "ja", "ko", "ar", "hi", "ru"])
    lowercase: bool = True


class MultilingualTokenizer:
    def __init__(self, config: Optional[MultilingualConfig] = None):
        self.config = config or MultilingualConfig()
        self._per_language_vocab: Dict[str, Dict[str, int]] = {}
        self._global_vocab: Dict[str, int] = {}
        logger.info("MultilingualTokenizer initialized for %d languages", len(self.config.languages))

    def detect_language(self, text: str) -> str:
        scores: Dict[str, int] = {}
        for lang, pattern in _SCRIPT_PATTERNS.items():
            scores[lang] = len(re.findall(pattern, text))
        if scores:
            return max(scores, key=scores.get)
        return "en"

    def tokenize(self, text: str, language: Optional[str] = None) -> List[str]:
        lang = language or self.detect_language(text)
        if self.config.lowercase:
            text = text.lower()
        if lang in _SCRIPT_PATTERNS:
            tokens = re.findall(_SCRIPT_PATTERNS[lang] + r"|\w+|[^\w\s]", text)
        else:
            tokens = re.findall(r"\w+|[^\w\s]", text)
        return tokens

    def encode(self, text: str, language: Optional[str] = None) -> List[int]:
        tokens = self.tokenize(text, language)
        vocab = self._per_language_vocab.get(language or "en", self._global_vocab)
        unk = vocab.get("<unk>", 0)
        return [vocab.get(t, unk) for t in tokens]

    def build_vocab(self, corpus: List[str], language: str) -> Dict[str, int]:
        from collections import Counter

        counts = Counter()
        for text in corpus:
            counts.update(self.tokenize(text, language))
        vocab = {"<unk>": 0, "<pad>": 1, "<s>": 2, "</s>": 3}
        idx = len(vocab)
        for token, _ in counts.most_common(self.config.vocab_size - idx):
            if token not in vocab:
                vocab[token] = idx
                idx += 1
        self._per_language_vocab[language] = vocab
        return vocab

    def decode(self, ids: List[int], language: Optional[str] = None) -> str:
        vocab = self._per_language_vocab.get(language or "en", self._global_vocab)
        inv = {v: k for k, v in vocab.items()}
        return "".join(inv.get(i, "<unk>") for i in ids)
