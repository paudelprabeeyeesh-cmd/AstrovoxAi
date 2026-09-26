import logging
import re
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MathTokenizerConfig:
    preserve_symbols: bool = True
    special_tokens: List[str] = None

    def __post_init__(self):
        if self.special_tokens is None:
            self.special_tokens = ["<num>", "<op>", "<func>"]


class MathTokenizer:
    def __init__(self, config: Optional[MathTokenizerConfig] = None):
        self.config = config or MathTokenizerConfig()
        self.math_symbols = set("+-*/=<>^∑∏∫√∞≈≠≤≥±∂∇∈⊂⊆∪∩∧∨¬→←↔")
        logger.info("Math tokenizer initialized")

    def tokenize(self, text: str) -> List[str]:
        tokens = []
        i = 0
        while i < len(text):
            if text[i] in self.math_symbols:
                tokens.append(text[i])
                i += 1
            elif text[i].isdigit() or text[i] == '.':
                j = i
                while j < len(text) and (text[j].isdigit() or text[j] == '.'):
                    j += 1
                tokens.append(text[i:j])
                i = j
            elif text[i].isalpha():
                j = i
                while j < len(text) and text[j].isalpha():
                    j += 1
                tokens.append(text[i:j])
                i = j
            elif text[i].isspace():
                i += 1
            else:
                tokens.append(text[i])
                i += 1
        return tokens
