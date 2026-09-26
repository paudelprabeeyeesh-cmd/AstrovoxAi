import logging
import re
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ProgrammingTokenizerConfig:
    preserve_whitespace: bool = False
    preserve_comments: bool = False
    language: str = "python"


class ProgrammingTokenizer:
    def __init__(self, config: Optional[ProgrammingTokenizerConfig] = None):
        self.config = config or ProgrammingTokenizerConfig()
        self.keywords = {
            "python": {"def", "class", "if", "else", "for", "while", "return", "import", "from", "as"},
            "javascript": {"function", "const", "let", "var", "if", "else", "for", "while", "return", "import"},
        }
        self.current_keywords = self.keywords.get(self.config.language, set())
        logger.info("Programming tokenizer initialized for %s", self.config.language)

    def tokenize(self, code: str) -> List[str]:
        tokens = []
        i = 0
        while i < len(code):
            if code[i].isspace():
                if self.config.preserve_whitespace:
                    tokens.append(code[i])
                i += 1
            elif code[i] in "(){}[]<>+-*/=!&|,.;:'\"":
                tokens.append(code[i])
                i += 1
            elif code[i].isdigit():
                j = i
                while j < len(code) and (code[j].isdigit() or code[j] == '.'):
                    j += 1
                tokens.append(code[i:j])
                i = j
            elif code[i].isalpha() or code[i] == '_':
                j = i
                while j < len(code) and (code[j].isalnum() or code[j] == '_'):
                    j += 1
                word = code[i:j]
                tokens.append(word)
                i = j
            else:
                tokens.append(code[i])
                i += 1
        return tokens
