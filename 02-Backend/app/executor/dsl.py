"""AI DSL: tokens, lexer, parser, and AST.

The DSL is a small imperative language for AI workflows.  Example:

    LOAD "document.pdf" AS doc
    SEARCH "authentication" IN doc LIMIT 10 AS hits
    SUMMARIZE hits LENGTH 200 AS summary
    GENERATE "report.md" FROM summary TEMPLATE "default"
    EMAIL "report.md" TO "alice@example.com"

Statements produce values bound to names; subsequent statements may
reference earlier bindings.  Loops and branches are also supported.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Token types
# ---------------------------------------------------------------------------


class TokenType(str, Enum):
    KEYWORD = "keyword"
    IDENTIFIER = "identifier"
    STRING = "string"
    NUMBER = "number"
    AS = "as"
    FROM = "from"
    IN = "in"
    TO = "to"
    LPAREN = "lparen"
    RPAREN = "rparen"
    COMMA = "comma"
    EQUALS = "equals"
    LBRACE = "lbrace"
    RBRACE = "rbrace"
    ARROW = "arrow"
    NEWLINE = "newline"
    EOF = "eof"


KEYWORDS = {
    "LOAD": TokenType.KEYWORD,
    "SAVE": TokenType.KEYWORD,
    "SEARCH": TokenType.KEYWORD,
    "SUMMARIZE": TokenType.KEYWORD,
    "GENERATE": TokenType.KEYWORD,
    "EMAIL": TokenType.KEYWORD,
    "TRANSLATE": TokenType.KEYWORD,
    "TRANSLATE_TO": TokenType.KEYWORD,
    "ANALYZE": TokenType.KEYWORD,
    "ASK": TokenType.KEYWORD,
    "IF": TokenType.KEYWORD,
    "ELSE": TokenType.KEYWORD,
    "FOR": TokenType.KEYWORD,
    "IN": TokenType.IN,
    "FROM": TokenType.FROM,
    "TO": TokenType.TO,
    "AS": TokenType.AS,
    "TEMPLATE": TokenType.KEYWORD,
    "LIMIT": TokenType.KEYWORD,
    "LENGTH": TokenType.KEYWORD,
    "LANGUAGE": TokenType.KEYWORD,
    "WITH": TokenType.KEYWORD,
    "PARALLEL": TokenType.KEYWORD,
}


@dataclass
class Token:
    type: TokenType
    value: Any
    line: int
    col: int

    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type.value, "value": self.value, "line": self.line, "col": self.col}


# ---------------------------------------------------------------------------
# Lexer
# ---------------------------------------------------------------------------


_STRING_PATTERN = re.compile(r'"((?:[^"\\]|\\.)*)"')


class LexerError(Exception):
    pass


class Lexer:
    def __init__(self, source: str) -> None:
        self.source = source
        self.pos = 0
        self.line = 1
        self.col = 1

    def _peek(self, offset: int = 0) -> str:
        idx = self.pos + offset
        if idx >= len(self.source):
            return ""
        return self.source[idx]

    def _advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _skip_whitespace(self) -> None:
        changed = True
        while changed and self.pos < len(self.source):
            changed = False
            if self.source[self.pos] in " \t\r":
                self._advance()
                changed = True
            elif self.source[self.pos] == "#":
                self._skip_comment()
                changed = True

    def _skip_comment(self) -> None:
        if self._peek() == "#":
            while self.pos < len(self.source) and self.source[self.pos] != "\n":
                self._advance()

    def _read_string(self) -> Token:
        start_line, start_col = self.line, self.col
        self._advance()  # opening quote
        match = _STRING_PATTERN.match(self.source, self.pos - 1)
        if not match:
            raise LexerError(f"unterminated string at {start_line}:{start_col}")
        value = match.group(1)
        # advance to end of match
        while self.pos < match.end():
            self._advance()
        return Token(TokenType.STRING, value, start_line, start_col)

    def _read_number(self) -> Token:
        start_line, start_col = self.line, self.col
        start = self.pos
        while self.pos < len(self.source) and (self.source[self.pos].isdigit() or self.source[self.pos] == "."):
            self._advance()
        text = self.source[start:self.pos]
        try:
            value: Any = int(text)
            if "." in text:
                value = float(text)
        except ValueError as exc:
            raise LexerError(f"invalid number '{text}' at {start_line}:{start_col}") from exc
        return Token(TokenType.NUMBER, value, start_line, start_col)

    def _read_identifier(self) -> Token:
        start_line, start_col = self.line, self.col
        start = self.pos
        while self.pos < len(self.source) and (self.source[self.pos].isalnum() or self.source[self.pos] in "_-"):
            self._advance()
        text = self.source[start:self.pos]
        keyword = KEYWORDS.get(text.upper())
        if keyword is not None:
            return Token(keyword, text.upper(), start_line, start_col)
        return Token(TokenType.IDENTIFIER, text, start_line, start_col)

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []
        while self.pos < len(self.source):
            self._skip_whitespace()
            if self.pos >= len(self.source):
                break
            ch = self._peek()
            if ch == "\n":
                self._advance()
                tokens.append(Token(TokenType.NEWLINE, "\n", self.line, self.col))
                continue
            if ch == "#":
                self._skip_comment()
                continue
            if ch == '"':
                tokens.append(self._read_string())
                continue
            if ch.isdigit():
                tokens.append(self._read_number())
                continue
            if ch.isalpha() or ch == "_":
                tokens.append(self._read_identifier())
                continue
            if ch == "(":
                self._advance()
                tokens.append(Token(TokenType.LPAREN, "(", self.line, self.col))
                continue
            if ch == ")":
                self._advance()
                tokens.append(Token(TokenType.RPAREN, ")", self.line, self.col))
                continue
            if ch == ",":
                self._advance()
                tokens.append(Token(TokenType.COMMA, ",", self.line, self.col))
                continue
            if ch == "=":
                self._advance()
                tokens.append(Token(TokenType.EQUALS, "=", self.line, self.col))
                continue
            if ch == "{":
                self._advance()
                tokens.append(Token(TokenType.LBRACE, "{", self.line, self.col))
                continue
            if ch == "}":
                self._advance()
                tokens.append(Token(TokenType.RBRACE, "}", self.line, self.col))
                continue
            if ch == "-" and self._peek(1) == ">":
                self._advance()
                self._advance()
                tokens.append(Token(TokenType.ARROW, "->", self.line, self.col))
                continue
            raise LexerError(f"unexpected character {ch!r} at {self.line}:{self.col}")
        tokens.append(Token(TokenType.EOF, None, self.line, self.col))
        return tokens


# ---------------------------------------------------------------------------
# AST nodes
# ---------------------------------------------------------------------------


@dataclass
class ASTNode:
    pass


@dataclass
class Statement(ASTNode):
    pass


@dataclass
class LoadStatement(Statement):
    target: str
    source: str
    alias: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"type": "LOAD", "target": self.target, "source": self.source, "alias": self.alias}


@dataclass
class SearchStatement(Statement):
    query: str
    target: Optional[str] = None  # variable name to search within
    limit: Optional[int] = None
    alias: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "SEARCH",
            "query": self.query,
            "target": self.target,
            "limit": self.limit,
            "alias": self.alias,
        }


@dataclass
class SummarizeStatement(Statement):
    target: str
    length: Optional[int] = None
    alias: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "SUMMARIZE",
            "target": self.target,
            "length": self.length,
            "alias": self.alias,
        }


@dataclass
class GenerateStatement(Statement):
    target: str
    template: Optional[str] = None
    alias: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "GENERATE",
            "target": self.target,
            "template": self.template,
            "alias": self.alias,
        }


@dataclass
class EmailStatement(Statement):
    target: str
    recipient: str

    def to_dict(self) -> Dict[str, Any]:
        return {"type": "EMAIL", "target": self.target, "recipient": self.recipient}


@dataclass
class AnalyzeStatement(Statement):
    target: str
    alias: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"type": "ANALYZE", "target": self.target, "alias": self.alias}


@dataclass
class AskStatement(Statement):
    prompt: str
    alias: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"type": "ASK", "prompt": self.prompt, "alias": self.alias}


@dataclass
class SaveStatement(Statement):
    target: str
    destination: str

    def to_dict(self) -> Dict[str, Any]:
        return {"type": "SAVE", "target": self.target, "destination": self.destination}


@dataclass
class ParallelBlock(Statement):
    statements: List[Statement] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"type": "PARALLEL", "statements": [s.to_dict() for s in self.statements]}


@dataclass
class Program:
    statements: List[Statement] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"type": "Program", "statements": [s.to_dict() for s in self.statements]}


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, tokens: List[Token]) -> None:
        self.tokens = tokens
        self.pos = 0

    def _peek(self, offset: int = 0) -> Token:
        idx = self.pos + offset
        if idx >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[idx]

    def _advance(self) -> Token:
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def _expect_keyword(self, name: str) -> Token:
        token = self._advance()
        if token.type != TokenType.KEYWORD or token.value != name:
            raise ParseError(f"expected {name}, got {token.value!r} at {token.line}:{token.col}")
        return token

    def _expect(self, *types: TokenType) -> Token:
        token = self._advance()
        if token.type not in types:
            names = ", ".join(t.value for t in types)
            raise ParseError(f"expected {names}, got {token.value!r} at {token.line}:{token.col}")
        return token

    def _skip_newlines(self) -> None:
        while self._peek().type == TokenType.NEWLINE:
            self._advance()

    def parse(self) -> Program:
        program = Program()
        self._skip_newlines()
        while self._peek().type != TokenType.EOF:
            stmt = self._parse_statement()
            if stmt is not None:
                program.statements.append(stmt)
            self._skip_newlines()
        return program

    def _parse_statement(self) -> Optional[Statement]:
        token = self._peek()
        if token.type != TokenType.KEYWORD:
            raise ParseError(f"expected keyword, got {token.value!r} at {token.line}:{token.col}")
        if token.value == "PARALLEL":
            return self._parse_parallel()
        return self._parse_command()

    def _parse_parallel(self) -> ParallelBlock:
        self._advance()  # PARALLEL
        self._expect(TokenType.LBRACE)
        self._skip_newlines()
        block = ParallelBlock()
        while self._peek().type != TokenType.RBRACE and self._peek().type != TokenType.EOF:
            stmt = self._parse_command()
            if stmt is not None:
                block.statements.append(stmt)
            self._skip_newlines()
        self._expect(TokenType.RBRACE)
        return block

    def _parse_command(self) -> Optional[Statement]:
        token = self._advance()
        keyword = token.value
        if keyword == "LOAD":
            return self._parse_load(token)
        if keyword == "SEARCH":
            return self._parse_search(token)
        if keyword == "SUMMARIZE":
            return self._parse_summarize(token)
        if keyword == "GENERATE":
            return self._parse_generate(token)
        if keyword == "EMAIL":
            return self._parse_email(token)
        if keyword == "ANALYZE":
            return self._parse_analyze(token)
        if keyword == "ASK":
            return self._parse_ask(token)
        if keyword == "SAVE":
            return self._parse_save(token)
        raise ParseError(f"unsupported keyword: {keyword} at {token.line}:{token.col}")

    def _consume_alias(self) -> Optional[str]:
        self._skip_newlines()
        if self._peek().type == TokenType.AS:
            self._advance()
            self._skip_newlines()
            ident = self._expect(TokenType.IDENTIFIER)
            return str(ident.value)
        return None

    def _parse_load(self, head: Token) -> LoadStatement:
        self._skip_newlines()
        source = self._expect(TokenType.STRING).value
        alias = self._consume_alias()
        return LoadStatement(target=str(source), source=str(source), alias=alias)

    def _parse_search(self, head: Token) -> SearchStatement:
        self._skip_newlines()
        query = self._expect(TokenType.STRING).value
        target: Optional[str] = None
        limit: Optional[int] = None
        while self._peek().type == TokenType.IN:
            self._advance()
            self._skip_newlines()
            target = self._expect(TokenType.IDENTIFIER).value
        if self._peek().type == TokenType.KEYWORD and self._peek().value == "LIMIT":
            self._advance()
            self._skip_newlines()
            limit = int(self._expect(TokenType.NUMBER).value)
        alias = self._consume_alias()
        return SearchStatement(query=str(query), target=target, limit=limit, alias=alias)

    def _parse_summarize(self, head: Token) -> SummarizeStatement:
        self._skip_newlines()
        target = self._expect(TokenType.IDENTIFIER).value
        length: Optional[int] = None
        if self._peek().type == TokenType.KEYWORD and self._peek().value == "LENGTH":
            self._advance()
            self._skip_newlines()
            length = int(self._expect(TokenType.NUMBER).value)
        alias = self._consume_alias()
        return SummarizeStatement(target=str(target), length=length, alias=alias)

    def _parse_generate(self, head: Token) -> GenerateStatement:
        self._skip_newlines()
        target = self._expect(TokenType.STRING).value
        source: Optional[str] = None
        if self._peek().type == TokenType.FROM:
            self._advance()
            self._skip_newlines()
            ident = self._expect(TokenType.IDENTIFIER)
            source = str(ident.value)
        template: Optional[str] = None
        if self._peek().type == TokenType.KEYWORD and self._peek().value == "TEMPLATE":
            self._advance()
            self._skip_newlines()
            template = self._expect(TokenType.STRING).value
        alias = self._consume_alias()
        return GenerateStatement(target=str(target), template=template, alias=alias)

    def _parse_email(self, head: Token) -> EmailStatement:
        self._skip_newlines()
        target = self._expect(TokenType.STRING).value
        self._skip_newlines()
        self._expect(TokenType.TO)
        self._skip_newlines()
        recipient = self._expect(TokenType.STRING).value
        return EmailStatement(target=str(target), recipient=str(recipient))

    def _parse_analyze(self, head: Token) -> AnalyzeStatement:
        self._skip_newlines()
        target = self._expect(TokenType.IDENTIFIER).value
        alias = self._consume_alias()
        return AnalyzeStatement(target=str(target), alias=alias)

    def _parse_ask(self, head: Token) -> AskStatement:
        self._skip_newlines()
        prompt = self._expect(TokenType.STRING).value
        alias = self._consume_alias()
        return AskStatement(prompt=str(prompt), alias=alias)

    def _parse_save(self, head: Token) -> SaveStatement:
        self._skip_newlines()
        target = self._expect(TokenType.IDENTIFIER).value
        self._skip_newlines()
        # Optional TO keyword
        if self._peek().type == TokenType.TO:
            self._advance()
            self._skip_newlines()
        destination = self._expect(TokenType.STRING).value
        return SaveStatement(target=str(target), destination=str(destination))


def parse(source: str) -> Program:
    tokens = Lexer(source).tokenize()
    return Parser(tokens).parse()