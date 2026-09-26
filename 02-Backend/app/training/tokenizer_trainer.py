"""
Tokenizer training pipeline for backend training workflows.
"""

from __future__ import annotations

import logging
import time
from typing import List, Optional

from app.tokenizer_data import Tokenizer, TokenizerConfig, TextCleaner, QualityFilter, Deduplicator, StreamingDataset, DatasetRegistry

logger = logging.getLogger(__name__)


class TokenizerTrainer:
    def __init__(self, vocab_size: int = 32000, min_pair_freq: int = 2):
        self.vocab_size = vocab_size
        self.min_pair_freq = min_pair_freq
        self.config = TokenizerConfig(vocab_size=vocab_size, min_pair_freq=min_pair_freq)

    def train(self, texts: List[str]) -> Tokenizer:
        tokenizer = Tokenizer(self.config)
        tokenizer.train(texts)
        logger.info("Trained tokenizer with vocab_size=%d", tokenizer.vocab_size)
        return tokenizer

    def train_from_file(self, path: str, limit: int = 10000) -> Tokenizer:
        cleaner = TextCleaner()
        qfilter = QualityFilter()
        dedup = Deduplicator()
        texts: List[str] = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                text = cleaner.clean(line)
                if not qfilter.accept(text):
                    continue
                if not dedup.is_unique(text):
                    continue
                texts.append(text)
                if len(texts) >= limit:
                    break
        return self.train(texts)

    def evaluate(self, tokenizer: Tokenizer, texts: List[str]) -> dict:
        total_chars = 0
        total_tokens = 0
        for text in texts:
            ids = tokenizer.encode(text)
            total_chars += len(text)
            total_tokens += len(ids)
        compression_ratio = total_chars / max(total_tokens, 1)
        return {
            "vocab_size": tokenizer.vocab_size,
            "total_tokens": total_tokens,
            "total_chars": total_chars,
            "compression_ratio": round(compression_ratio, 3),
        }
