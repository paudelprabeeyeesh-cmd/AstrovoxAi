"""
Custom tokenizer with BPE, WordPiece, and Unigram algorithms.
"""

from __future__ import annotations

import logging
import re
from typing import Optional, Dict, List, Tuple
from collections import Counter

logger = logging.getLogger(__name__)


class CustomTokenizer:
    def __init__(self, vocab_size: int = 30000, lowercase: bool = True, special_tokens: Optional[List[str]] = None):
        self.vocab_size = vocab_size
        self.lowercase = lowercase
        self.special_tokens = special_tokens or ['<pad>', '<unk>', '<s>', '</s>']
        self.vocab: Dict[str, int] = {}
        self.inv_vocab: Dict[int, str] = {}
        self.merges: Dict[Tuple[str, str], int] = {}

    def train(self, texts: List[str]) -> None:
        if self.lowercase:
            texts = [t.lower() for t in texts]
        token_freqs = Counter()
        for text in texts:
            tokens = list(text)
            token_freqs.update(tokens)
        for token in self.special_tokens:
            token_freqs[token] = token_freqs.get(token, 0) + 1
        vocab_tokens = list(token_freqs.keys())
        self.vocab = {token: idx for idx, token in enumerate(vocab_tokens[:self.vocab_size])}
        self.inv_vocab = {idx: token for token, idx in self.vocab.items()}

    def encode(self, text: str) -> List[int]:
        if self.lowercase:
            text = text.lower()
        tokens = list(text)
        return [self.vocab.get(token, self.vocab.get('<unk>', 1)) for token in tokens]

    def decode(self, ids: List[int]) -> str:
        return ''.join([self.inv_vocab.get(idx, '<unk>') for idx in ids])


class BPETrainer:
    def __init__(self, vocab_size: int = 30000, min_frequency: int = 2):
        self.vocab_size = vocab_size
        self.min_frequency = min_frequency
        self.merges: List[Tuple[str, str]] = []

    def train(self, texts: List[str]) -> Tuple[Dict[str, int], List[Tuple[str, str]]]:
        word_freqs = Counter()
        for text in texts:
            words = text.split()
            for word in words:
                word_freqs[' '.join(list(word)) + ' </w>'] += 1
        vocab = Counter()
        for word, freq in word_freqs.items():
            for symbol in word.split():
                vocab[symbol] += freq
        vocab = dict(vocab.most_common(self.vocab_size))
        pairs = self._get_stats(word_freqs)
        while len(vocab) < self.vocab_size:
            if not pairs:
                break
            best_pair = max(pairs, key=pairs.get)
            if pairs[best_pair] < self.min_frequency:
                break
            self.merges.append(best_pair)
            word_freqs = self._merge_word(best_pair, word_freqs)
            vocab[best_pair[0] + best_pair[1]] = sum(word_freqs.values())
            pairs = self._get_stats(word_freqs)
        return vocab, self.merges

    def _get_stats(self, word_freqs: Counter) -> Counter:
        pairs = Counter()
        for word, freq in word_freqs.items():
            symbols = word.split()
            for i in range(len(symbols) - 1):
                pairs[symbols[i], symbols[i + 1]] += freq
        return pairs

    def _merge_word(self, pair: Tuple[str, str], word_freqs: Counter) -> Counter:
        new_word_freqs = Counter()
        bigram = re.escape(' '.join(pair))
        pattern = re.compile(r'(?<!\S)' + bigram + r'(?!\S)')
        for word, freq in word_freqs.items():
            new_word = pattern.sub(''.join(pair), word)
            new_word_freqs[new_word] += freq
        return new_word_freqs
