"""Mathematical tokenizer for ASTROVOX_AI."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MathTokenizerConfig:
    preserve_symbols: bool = True
    special_tokens: List[str] = field(default_factory=lambda: ["<num>", "<op>", "<func>", "<var>", "<frac>", "<sqrt>", "<sum>", "<int>", "<matrix>"])
    latex_mode: bool = True


class MathTokenizer:
    def __init__(self, config: Optional[MathTokenizerConfig] = None):
        self.config = config or MathTokenizerConfig()
        self.math_symbols = set("+-*/=<>^∑∏∫√∞≈≠≤≥±∂∇∈⊂⊆∪∩∧∨¬→←↔")
        self._latex_patterns = {
            "frac": re.compile(r"\\frac\{[^}]*\}\{[^}]*\}"),
            "sqrt": re.compile(r"\\sqrt\{[^}]*\}"),
            "sum": re.compile(r"\\sum_?(\^?\{[^}]*\})?_?(\_?\{[^}]*\})?"),
            "int": re.compile(r"\\int_?(\^?\{[^}]*\})?_?(\_?\{[^}]*\})?"),
            "matrix": re.compile(r"\\begin\{[a-z]+\}.*?\\end\{[a-z]+\}", re.DOTALL),
            "command": re.compile(r"\\[a-zA-Z]+"),
            "number": re.compile(r"\d+\.?\d*"),
            "variable": re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*"),
        }
        logger.info("MathTokenizer initialized")

    def tokenize(self, text: str) -> List[str]:
        if self.config.latex_mode:
            return self._tokenize_latex(text)
        return self._tokenize_plain(text)

    def _tokenize_latex(self, text: str) -> List[str]:
        tokens: List[str] = []
        i = 0
        while i < len(text):
            if text[i] == "\\":
                matched = False
                for name, pattern in self._latex_patterns.items():
                    m = pattern.match(text, i)
                    if m:
                        tokens.append(f"<{name}>")
                        tokens.append(m.group(0))
                        i = m.end()
                        matched = True
                        break
                if not matched:
                    tokens.append(text[i])
                    i += 1
            elif text[i] in self.math_symbols:
                tokens.append(text[i])
                i += 1
            elif text[i].isdigit() or (text[i] == "." and i + 1 < len(text) and text[i + 1].isdigit()):
                j = i
                while j < len(text) and (text[j].isdigit() or text[j] == "."):
                    j += 1
                tokens.append(f"<num>{text[i:j]}")
                i = j
            elif text[i].isalpha() or text[i] == "_":
                j = i
                while j < len(text) and (text[j].isalnum() or text[j] == "_"):
                    j += 1
                tokens.append(f"<var>{text[i:j]}")
                i = j
            elif text[i].isspace():
                i += 1
            else:
                tokens.append(text[i])
                i += 1
        return tokens

    def _tokenize_plain(self, text: str) -> List[str]:
        tokens: List[str] = []
        i = 0
        while i < len(text):
            if text[i] in self.math_symbols:
                tokens.append(text[i])
                i += 1
            elif text[i].isdigit() or text[i] == ".":
                j = i
                while j < len(text) and (text[j].isdigit() or text[j] == "." or text[j] in "eE+-"):
                    j += 1
                tokens.append(f"<num>{text[i:j]}")
                i = j
            elif text[i].isalpha():
                j = i
                while j < len(text) and text[j].isalpha():
                    j += 1
                tokens.append(f"<func>{text[i:j]}")
                i = j
            elif text[i].isspace():
                i += 1
            else:
                tokens.append(text[i])
                i += 1
        return tokens

    def encode(self, text: str) -> List[int]:
        tokens = self.tokenize(text)
        special_ids = {token: idx for idx, token in enumerate(self.config.special_tokens)}
        return [special_ids.get(t, hash(t) % (2**16)) for t in tokens]

    def decode(self, ids: List[int]) -> str:
        special = {idx: token for idx, token in enumerate(self.config.special_tokens)}
        return " ".join(special.get(i, str(i)) for i in ids)

    def latex_to_tokens(self, latex: str) -> List[str]:
        return self._tokenize_latex(latex)
