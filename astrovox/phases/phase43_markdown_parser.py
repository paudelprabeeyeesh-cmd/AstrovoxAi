"""Markdown document parser producing structured content."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Literal


@dataclass
class MDBlock:
    """A block of parsed markdown content."""
    kind: str  # heading, paragraph, code, list, blockquote
    content: str
    level: int = 0

    def to_dict(self) -> dict:
        return {"kind": self.kind, "content": self.content, "level": self.level}


@dataclass
class MarkdownDocument:
    """A parsed Markdown document."""
    path: str = ""
    blocks: list[MDBlock] = field(default_factory=list)
    title: str = ""

    def to_text(self) -> str:
        parts = []
        for b in self.blocks:
            if b.kind == "heading":
                parts.append(f"{'#' * b.level} {b.content}")
            elif b.kind == "code":
                parts.append(f"```\n{b.content}\n```")
            else:
                parts.append(b.content)
        return "\n\n".join(parts)

    def to_dict(self) -> dict:
        return {"path": self.path, "title": self.title,
                "blocks": [b.to_dict() for b in self.blocks]}


class MarkdownParser:
    """Parse Markdown files into structured blocks."""

    HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
    CODE_BLOCK_RE = re.compile(r"^```(?:\w+)?\n(.*)^```", re.S)
    LIST_RE = re.compile(r"^[-*+]\s+(.*)$")
    QUOTE_RE = re.compile(r"^>\s*(.*)$")

    def parse(self, path: str | Path) -> MarkdownDocument:
        """Parse a Markdown file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Markdown not found: {path}")
        text = path.read_text(encoding="utf-8", errors="replace")
        return self.parse_text(text, str(path))

    def parse_text(self, text: str, path: str = "") -> MarkdownDocument:
        """Parse Markdown text."""
        doc = MarkdownDocument(path=path)
        lines = text.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            m = self.HEADING_RE.match(line)
            if m:
                doc.blocks.append(MDBlock(kind="heading", level=len(m.group(1)), content=m.group(2)))
                if doc.title == "" and len(m.group(1)) == 1:
                    doc.title = m.group(2)
                i += 1
                continue
            if line.startswith("```"):
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].startswith("```"):
                    code_lines.append(lines[i])
                    i += 1
                doc.blocks.append(MDBlock(kind="code", content="\n".join(code_lines)))
                i += 1
                continue
            if self.LIST_RE.match(line):
                items = []
                while i < len(lines) and self.LIST_RE.match(lines[i]):
                    items.append(self.LIST_RE.match(lines[i]).group(1))
                    i += 1
                doc.blocks.append(MDBlock(kind="list", content="\n".join(items)))
                continue
            if self.QUOTE_RE.match(line):
                items = []
                while i < len(lines) and self.QUOTE_RE.match(lines[i]):
                    items.append(self.QUOTE_RE.match(lines[i]).group(1))
                    i += 1
                doc.blocks.append(MDBlock(kind="blockquote", content="\n".join(items)))
                continue
            doc.blocks.append(MDBlock(kind="paragraph", content=line))
            i += 1
        return doc

    def parse_many(self, paths: list[str]) -> list[MarkdownDocument]:
        """Parse multiple Markdown files."""
        return [self.parse(p) for p in paths]
