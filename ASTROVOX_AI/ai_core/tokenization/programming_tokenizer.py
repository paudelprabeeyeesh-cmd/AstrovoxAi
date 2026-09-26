"""Programming language tokenizer for ASTROVOX_AI."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class ProgrammingTokenizerConfig:
    language: str = "python"
    preserve_whitespace: bool = False
    preserve_comments: bool = False
    preserve_strings: bool = True
    preserve_numbers: bool = True


class ProgrammingTokenizer:
    def __init__(self, config: Optional[ProgrammingTokenizerConfig] = None):
        self.config = config or ProgrammingTokenizerConfig()
        self._patterns = self._build_patterns()
        logger.info("ProgrammingTokenizer initialized for %s", self.config.language)

    def _build_patterns(self) -> Dict[str, Optional[re.Pattern]]:
        lang = self.config.language
        keywords = self._keywords(lang)
        comment_single = self._comment_single(lang)
        comment_multi_start, comment_multi_end = self._comment_multi(lang)
        return {
            "comment_single": re.compile(comment_single),
            "comment_multi_start": re.compile(comment_multi_start) if comment_multi_start else None,
            "comment_multi_end": re.compile(comment_multi_end) if comment_multi_end else None,
            "string": re.compile(r"([\"'])(?:(?=(\\?))\2.)*?\1"),
            "number": re.compile(r"\b\d+\.?\d*\b"),
            "operator": re.compile(r"([+\-*/%=<>!&|^~]{1,2})"),
            "delimiter": re.compile(r"([{}()\[\];,.])"),
            "identifier": re.compile(r"([A-Za-z_][A-Za-z0-9_]*)"),
            "keywords": re.compile(r"\b(" + "|".join(map(re.escape, keywords)) + r")\b") if keywords else None,
        }

    def _keywords(self, lang: str) -> Set[str]:
        kw: Dict[str, Set[str]] = {
            "python": {"def", "class", "if", "elif", "else", "for", "while", "return", "import", "from", "as", "try", "except", "with", "yield", "lambda", "pass", "break", "continue", "and", "or", "not", "in", "is", "None", "True", "False", "async", "await"},
            "javascript": {"function", "const", "let", "var", "if", "else", "for", "while", "return", "import", "from", "as", "try", "catch", "class", "extends", "new", "this", "async", "await", "yield", "switch", "case", "break", "default"},
            "rust": {"fn", "let", "mut", "if", "else", "for", "while", "return", "match", "struct", "enum", "impl", "trait", "pub", "use", "mod", "crate", "self", "super", "async", "await", "move", "ref", "static", "const"},
            "go": {"func", "var", "const", "if", "else", "for", "range", "return", "import", "package", "struct", "interface", "map", "chan", "go", "select", "case", "default", "fallthrough", "defer"},
            "java": {"public", "private", "protected", "static", "final", "class", "interface", "extends", "implements", "if", "else", "for", "while", "return", "new", "this", "super", "import", "package", "try", "catch", "throw", "throws"},
        }
        return kw.get(lang, set())

    def _comment_single(self, lang: str) -> str:
        return {"python": r"#.*", "javascript": r"//.*", "rust": r"//.*", "go": r"//.*", "java": r"//.*"}.get(lang, r"//.*")

    def _comment_multi(self, lang: str) -> tuple:
        return {"python": (r'"""', r'"""'), "javascript": (r"/\*", r"\*/"), "rust": (r"/\*", r"\*/"), "go": (r"/\*", r"\*/"), "java": (r"/\*", r"\*/")}.get(lang, (None, None))

    def tokenize(self, code: str) -> List[str]:
        tokens: List[str] = []
        i = 0
        in_multiline = False
        while i < len(code):
            if in_multiline:
                end_pat = self._patterns.get("comment_multi_end")
                if end_pat:
                    m = end_pat.search(code, i)
                    if m:
                        if self.config.preserve_comments:
                            tokens.append(code[i : m.end()])
                        i = m.end()
                        in_multiline = False
                        continue
                tokens.append(code[i])
                i += 1
                continue

            if self.config.preserve_comments:
                single = self._patterns.get("comment_single")
                if single:
                    m = single.match(code, i)
                    if m:
                        tokens.append(m.group(0))
                        i = m.end()
                        continue
                start_pat = self._patterns.get("comment_multi_start")
                if start_pat and start_pat.match(code, i):
                    in_multiline = True
                    continue

            string_pat = self._patterns.get("string")
            if string_pat and self.config.preserve_strings:
                m = string_pat.match(code, i)
                if m:
                    tokens.append(m.group(0))
                    i = m.end()
                    continue

            number_pat = self._patterns.get("number")
            if number_pat and self.config.preserve_numbers:
                m = number_pat.match(code, i)
                if m:
                    tokens.append(m.group(0))
                    i = m.end()
                    continue

            kw_pat = self._patterns.get("keywords")
            if kw_pat:
                m = kw_pat.match(code, i)
                if m:
                    tokens.append(m.group(0))
                    i = m.end()
                    continue

            op_pat = self._patterns.get("operator")
            if op_pat:
                m = op_pat.match(code, i)
                if m:
                    tokens.append(m.group(0))
                    i = m.end()
                    continue

            delim_pat = self._patterns.get("delimiter")
            if delim_pat:
                m = delim_pat.match(code, i)
                if m:
                    tokens.append(m.group(0))
                    i = m.end()
                    continue

            ident_pat = self._patterns.get("identifier")
            if ident_pat:
                m = ident_pat.match(code, i)
                if m:
                    tokens.append(m.group(0))
                    i = m.end()
                    continue

            if code[i].isspace():
                if self.config.preserve_whitespace:
                    tokens.append(code[i])
                i += 1
            else:
                tokens.append(code[i])
                i += 1
        return tokens

    def encode(self, code: str) -> List[int]:
        tokens = self.tokenize(code)
        return [hash(t) % (2**16) for t in tokens]

    def decode(self, ids: List[int]) -> str:
        return " ".join(str(i) for i in ids)
