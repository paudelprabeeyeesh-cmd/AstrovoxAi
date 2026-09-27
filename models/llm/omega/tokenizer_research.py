"""Omega-2: Tokenizer research with adaptive vocabulary and online learning."""

import json
import logging
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class TokenizerConfig:
    vocab_size: int = 32768
    min_frequency: int = 2
    max_token_length: int = 16
    special_tokens: Dict[str, int] = field(default_factory=lambda: {"<pad>": 0, "<unk>": 1, "<bos>": 2, "<eos>": 3, "<mask>": 4})
    lowercase: bool = True
    normalize_unicode: bool = True


class BaseTokenizer:
    def __init__(self, config: Optional[TokenizerConfig] = None):
        self.config = config or TokenizerConfig()
        self.vocab: Dict[str, int] = dict(self.config.special_tokens)
        self.inverse_vocab: Dict[int, str] = {v: k for k, v in self.vocab.items()}

    def encode(self, text: str) -> List[int]:
        raise NotImplementedError

    def decode(self, ids: List[int]) -> str:
        return "".join(self.inverse_vocab.get(i, "<unk>") for i in ids)

    def add_tokens(self, tokens: List[str]) -> int:
        added = 0
        for token in tokens:
            if token not in self.vocab:
                self.vocab[token] = len(self.vocab)
                self.inverse_vocab[len(self.inverse_vocab)] = token
                added += 1
        return added


class WordPieceTokenizer(BaseTokenizer):
    def __init__(self, config: Optional[TokenizerConfig] = None):
        super().__init__(config)

    def encode(self, text: str) -> List[int]:
        if self.config.lowercase:
            text = text.lower()
        tokens = []
        for word in text.split():
            if word in self.vocab:
                tokens.append(self.vocab[word])
            else:
                subword = self._wordpiece_tokenize(word)
                tokens.extend(self.vocab.get(t, self.vocab["<unk>"]) for t in subword)
        return tokens

    def _wordpiece_tokenize(self, word: str) -> List[str]:
        tokens = []
        start = 0
        while start < len(word):
            end = len(word)
            cur_substr = None
            while start < end:
                substr = word[start:end]
                if start > 0:
                    substr = "##" + substr
                if substr in self.vocab:
                    cur_substr = substr
                    break
                end -= 1
            if cur_substr is None:
                tokens.append("<unk>")
                break
            tokens.append(cur_substr)
            start = end
        return tokens


class BPE(BaseTokenizer):
    def __init__(self, config: Optional[TokenizerConfig] = None):
        super().__init__(config)
        self.merges: Dict[Tuple[str, str], str] = {}

    def train(self, corpus: List[str], num_merges: int = 1000) -> None:
        vocab_counter = Counter()
        for text in corpus:
            words = self._preprocess(text)
            vocab_counter.update(words)
        for _ in range(num_merges):
            pair_counts = Counter()
            for word, count in vocab_counter.items():
                symbols = word.split()
                for i in range(len(symbols) - 1):
                    pair = (symbols[i], symbols[i + 1])
                    pair_counts[pair] += count
            if not pair_counts:
                break
            best_pair = pair_counts.most_common(1)[0][0]
            new_symbol = "".join(best_pair)
            self.merges[best_pair] = new_symbol
            new_vocab = Counter()
            for word, count in vocab_counter.items():
                symbols = word.split()
                new_word = self._merge_pair(symbols, best_pair, new_symbol)
                new_vocab[new_word] = count
            vocab_counter = new_vocab
        self.vocab = {**self.config.special_tokens, **{token: i + len(self.config.special_tokens) for i, token in enumerate(vocab_counter.keys())}}
        self.inverse_vocab = {v: k for k, v in self.vocab.items()}

    def encode(self, text: str) -> List[int]:
        if self.config.lowercase:
            text = text.lower()
        word = " ".join(self._preprocess(text))
        for (a, b), merged in self.merges.items():
            word = word.replace(f"{a} {b}", merged)
        tokens = word.split()
        return [self.vocab.get(t, self.vocab["<unk>"]) for t in tokens]

    @staticmethod
    def _preprocess(text: str) -> List[str]:
        return [" ".join(list(word)) for word in text.split()]

    @staticmethod
    def _merge_pair(symbols: List[str], pair: Tuple[str, str], new_symbol: str) -> str:
        result = []
        i = 0
        while i < len(symbols):
            if i < len(symbols) - 1 and symbols[i] == pair[0] and symbols[i + 1] == pair[1]:
                result.append(new_symbol)
                i += 2
            else:
                result.append(symbols[i])
                i += 1
        return " ".join(result)


class UnigramTokenizer(BaseTokenizer):
    def __init__(self, config: Optional[TokenizerConfig] = None):
        super().__init__(config)
        self._token_scores: Dict[str, float] = {}

    def train(self, corpus: List[str], vocab_size: int = 30000) -> None:
        from collections import Counter
        word_counts = Counter()
        for text in corpus:
            word_counts.update(text.split())
        self._token_scores = {word: -count for word, count in word_counts.items()}
        for _ in range(vocab_size - len(self._token_scores)):
            pass  # Placeholder for EM iterations
        self.vocab = {**self.config.special_tokens, **{token: i + len(self.config.special_tokens) for i, token in enumerate(self._token_scores.keys())}}
        self.inverse_vocab = {v: k for k, v in self.vocab.items()}

    def encode(self, text: str) -> List[int]:
        if self.config.lowercase:
            text = text.lower()
        return [self.vocab.get(word, self.vocab["<unk>"]) for word in text.split()]


class OnlineTokenizerLearner:
    def __init__(self, tokenizer: BaseTokenizer, buffer_size: int = 10000, update_interval: int = 1000):
        self.tokenizer = tokenizer
        self.buffer_size = buffer_size
        self.update_interval = update_interval
        self._buffer: List[str] = []
        self._step = 0

    def update(self, text: str) -> None:
        self._buffer.append(text)
        if len(self._buffer) >= self.buffer_size:
            self._retrain()

    def _retrain(self) -> None:
        new_tokens = Counter()
        for text in self._buffer:
            tokens = re.findall(r"\w+", text.lower())
            new_tokens.update(tokens)
        added = self.tokenizer.add_tokens([t for t, c in new_tokens.items() if c >= self.config.min_frequency])
        logger.info("Online tokenizer update: added %d new tokens", added)
        self._buffer.clear()


class AdaptiveVocab:
    def __init__(self, base_tokenizer: BaseTokenizer, growth_rate: float = 0.1):
        self.base_tokenizer = base_tokenizer
        self.growth_rate = growth_rate
        self._usage_counts: Counter = Counter()

    def adapt(self, texts: List[str]) -> BaseTokenizer:
        for text in texts:
            self._usage_counts.update(re.findall(r"\w+", text.lower()))
        threshold = int(len(self._usage_counts) * self.growth_rate)
        new_tokens = [t for t, c in self._usage_counts.most_common(threshold) if t not in self.base_tokenizer.vocab]
        self.base_tokenizer.add_tokens(new_tokens)
        return self.base_tokenizer


@dataclass
class TokenizerResearchResult:
    tokenizer_name: str
    vocab_size: int
    compression_ratio: float
    fertility: float
    runtime_ms: float


class TokenizerResearch:
    def __init__(self, config: Optional[TokenizerConfig] = None):
        self.config = config or TokenizerConfig()
        self.tokenizers: Dict[str, BaseTokenizer] = {
            "wordpiece": WordPieceTokenizer(self.config),
            "bpe": BPE(self.config),
            "unigram": UnigramTokenizer(self.config),
        }
        self.online_learners: Dict[str, OnlineTokenizerLearner] = {}

    def train_all(self, corpus: List[str]) -> None:
        self.tokenizers["bpe"].train(corpus)
        self.tokenizers["unigram"].train(corpus)
        for name, tokenizer in self.tokenizers.items():
            self.online_learners[name] = OnlineTokenizerLearner(tokenizer)

    def evaluate(self, text: str) -> Dict[str, TokenizerResearchResult]:
        results = {}
        for name, tokenizer in self.tokenizers.items():
            start = time.perf_counter()
            ids = tokenizer.encode(text)
            runtime = (time.perf_counter() - start) * 1000
            results[name] = TokenizerResearchResult(
                tokenizer_name=name,
                vocab_size=len(tokenizer.vocab),
                compression_ratio=len(text) / max(len(ids), 1),
                fertility=len(ids) / max(len(text.split()), 1),
                runtime_ms=runtime,
            )
        return results

    def get_best_tokenizer(self, text: str) -> str:
        results = self.evaluate(text)
        return min(results, key=lambda k: results[k].runtime_ms)
