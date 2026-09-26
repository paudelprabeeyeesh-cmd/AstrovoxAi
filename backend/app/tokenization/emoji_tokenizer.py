import logging
import re
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class EmojiTokenizerConfig:
    include_emoji: bool = True
    emoji_vocab_path: Optional[str] = None


class EmojiTokenizer:
    def __init__(self, config: Optional[EmojiTokenizerConfig] = None):
        self.config = config or EmojiTokenizerConfig()
        self.emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "\U0001F1E0-\U0001F1FF"
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE
        )
        logger.info("Emoji tokenizer initialized")

    def extract_emojis(self, text: str) -> List[str]:
        return self.emoji_pattern.findall(text)

    def replace_emojis(self, text: str, placeholder: str = "<emoji>") -> str:
        return self.emoji_pattern.sub(placeholder, text)

    def tokenize(self, text: str) -> List[str]:
        if not self.config.include_emoji:
            text = self.replace_emojis(text)
        words = text.split()
        tokens = []
        for word in words:
            emojis = self.extract_emojis(word)
            if emojis:
                tokens.extend(emojis)
                word = self.replace_emojis(word)
                tokens.extend(word.split())
            else:
                tokens.append(word)
        return tokens
