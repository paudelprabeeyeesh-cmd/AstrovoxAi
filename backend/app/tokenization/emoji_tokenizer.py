"""Emoji tokenizer with full Unicode emoji support."""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\U0001F926-\U0001F937"
    "\U00010000-\U0010FFFF"
    "\u200d"
    "\u2640-\u2642"
    "\u2600-\u2B55"
    "\u200d"
    "\u23cf"
    "\u23e9"
    "\u231a"
    "\ufe0f"
    "\u3030"
    "]+",
    flags=re.UNICODE,
)


@dataclass
class EmojiTokenizerConfig:
    include_emoji: bool = True
    emoji_vocab_path: Optional[str] = None
    replace_with_placeholder: bool = False
    placeholder: str = "<emoji>"


class EmojiTokenizer:
    def __init__(self, config: Optional[EmojiTokenizerConfig] = None):
        self.config = config or EmojiTokenizerConfig()
        self.emoji_pattern = _EMOJI_PATTERN
        self._emoji_vocab: Dict[str, int] = {}
        self._load_vocab()
        logger.info("Emoji tokenizer initialized")

    def _load_vocab(self) -> None:
        if self.config.emoji_vocab_path:
            import json

            try:
                with open(self.config.emoji_vocab_path, "r", encoding="utf-8") as f:
                    self._emoji_vocab = json.load(f)
            except (OSError, json.JSONDecodeError):
                logger.warning("Failed to load emoji vocab from %s", self.config.emoji_vocab_path)

    def extract_emojis(self, text: str) -> List[str]:
        return self.emoji_pattern.findall(text)

    def replace_emojis(self, text: str, placeholder: Optional[str] = None) -> str:
        ph = placeholder or self.config.placeholder
        return self.emoji_pattern.sub(ph, text)

    def tokenize(self, text: str) -> List[str]:
        if self.config.replace_with_placeholder:
            text = self.replace_emojis(text)
            return text.split()
        tokens: List[str] = []
        parts = self.emoji_pattern.split(text)
        emojis = self.emoji_pattern.findall(text)
        for i, part in enumerate(parts):
            if part:
                tokens.extend(part.split())
            if i < len(emojis):
                tokens.append(emojis[i])
        return [t for t in tokens if t]

    def encode(self, text: str) -> List[int]:
        tokens = self.tokenize(text)
        return [self._emoji_vocab.get(t, hash(t) % (2**16)) for t in tokens]

    def decode(self, ids: List[int]) -> str:
        inv = {v: k for k, v in self._emoji_vocab.items()}
        return " ".join(inv.get(i, f"<unk:{i}>") for i in ids)

    def has_emoji(self, text: str) -> bool:
        return bool(self.emoji_pattern.search(text))

    def count_emoji(self, text: str) -> int:
        return len(self.extract_emojis(text))

    def describe(self, text: str) -> List[Dict[str, str]]:
        results = []
        for match in self.emoji_pattern.finditer(text):
            emoji = match.group()
            results.append(
                {
                    "emoji": emoji,
                    "start": match.start(),
                    "end": match.end(),
                    "name": unicodedata.name(emoji[0], "UNKNOWN") if emoji else "UNKNOWN",
                }
            )
        return results

