"""Tokenization pipeline orchestrator."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Union

from .bpe_trainer import BPETrainer, BPETrainerConfig
from .sentencepiece_trainer import SentencePieceTrainer
from .dynamic_vocabulary import DynamicVocabulary, DynamicVocabularyConfig
from .unicode_normalization import UnicodeNormalizer
from .emoji_tokenizer import EmojiTokenizer, EmojiTokenizerConfig
from .multilingual_tokenizer import MultilingualTokenizer, MultilingualTokenizerConfig
from .math_tokenizer import MathTokenizer, MathTokenizerConfig
from .programming_tokenizer import ProgrammingTokenizer, ProgrammingTokenizerConfig

logger = logging.getLogger(__name__)


@dataclass
class TokenizationConfig:
    algorithm: str = "bpe"
    vocab_size: int = 32000
    min_frequency: int = 2
    lowercase: bool = False
    normalization_form: str = "NFKC"
    language: Optional[str] = None
    preserve_comments: bool = False
    preserve_strings: bool = True
    emoji_handling: str = "preserve"


class TokenizationPipeline:
    def __init__(self, config: Optional[TokenizationConfig] = None):
        self.config = config or TokenizationConfig()
        self._normalizer = UnicodeNormalizer(self.config.normalization_form)
        self._emoji = EmojiTokenizer(EmojiTokenizerConfig(replace_with_placeholder=(self.config.emoji_handling == "replace")))
        self._bpe: Optional[BPETrainer] = None
        self._sp: Optional[SentencePieceTrainer] = None
        self._dynamic: Optional[DynamicVocabulary] = None
        self._multilingual: Optional[MultilingualTokenizer] = None
        self._math: Optional[MathTokenizer] = None
        self._programming: Optional[ProgrammingTokenizer] = None
        logger.info("Tokenization pipeline initialized with algorithm=%s", self.config.algorithm)

    def normalize(self, text: str) -> str:
        return self._normalizer.normalize(text)

    def handle_emoji(self, text: str) -> str:
        return self._emoji.replace_emojis(text) if self.config.emoji_handling == "replace" else text

    def train_bpe(self, corpus: List[str]) -> BPETrainer:
        self._bpe = BPETrainer(BPETrainerConfig(vocab_size=self.config.vocab_size, min_frequency=self.config.min_frequency, lowercase=self.config.lowercase, normalization_form=self.config.normalization_form))
        self._bpe.train(corpus)
        return self._bpe

    def train_sentencepiece(self, input_file: str, model_prefix: str) -> str:
        self._sp = SentencePieceTrainer()
        return self._sp.train(input_file, model_prefix, vocab_size=self.config.vocab_size)

    def init_dynamic_vocab(self) -> DynamicVocabulary:
        self._dynamic = DynamicVocabulary(DynamicVocabularyConfig(max_vocab_size=self.config.vocab_size, min_frequency=self.config.min_frequency))
        return self._dynamic

    def init_multilingual(self) -> MultilingualTokenizer:
        self._multilingual = MultilingualTokenizer(MultilingualTokenizerConfig(vocab_size=self.config.vocab_size))
        return self._multilingual

    def init_math(self) -> MathTokenizer:
        self._math = MathTokenizer(MathTokenizerConfig())
        return self._math

    def init_programming(self, language: Optional[str] = None) -> ProgrammingTokenizer:
        lang = language or self.config.language or "python"
        self._programming = ProgrammingTokenizer(ProgrammingTokenizerConfig(language=lang, preserve_comments=self.config.preserve_comments, preserve_strings=self.config.preserve_strings))
        return self._programming

    def encode(self, text: str, language: Optional[str] = None) -> List[int]:
        text = self.normalize(text)
        text = self.handle_emoji(text)
        if self.config.algorithm == "bpe" and self._bpe is not None:
            return self._bpe.encode(text)
        if self.config.algorithm == "sentencepiece" and self._sp is not None:
            return self._sp.encode(text)
        if self.config.algorithm == "dynamic" and self._dynamic is not None:
            return self._dynamic.encode(text)
        if self.config.algorithm == "multilingual" and self._multilingual is not None:
            return self._multilingual.encode(text, language=language)
        if self.config.algorithm == "math" and self._math is not None:
            return self._math.encode(text)
        if self.config.algorithm == "programming" and self._programming is not None:
            return self._programming.encode(text)
        raise RuntimeError(f"No trained tokenizer for algorithm: {self.config.algorithm}")

    def tokenize(self, text: str, mode: str = "text") -> Union[List[str], List[int]]:
        text = self.normalize(text)
        text = self.handle_emoji(text)
        if mode == "math":
            tok = self.init_math()
            return tok.tokenize(text)
        if mode == "programming":
            tok = self.init_programming()
            return tok.tokenize(text)
        if mode == "multilingual":
            tok = self.init_multilingual()
            return tok.tokenize(text)
        if self._bpe is None:
            self.train_bpe([text])
        return self._bpe.encode(text)
