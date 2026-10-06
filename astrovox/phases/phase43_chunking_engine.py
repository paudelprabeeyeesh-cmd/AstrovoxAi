"""Recursive semantic chunking with configurable size and overlap."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field


@dataclass
class Chunk:
    """A text chunk with metadata."""
    id: str
    text: str
    start: int = 0
    end: int = 0
    parent_id: str | None = None
    level: int = 0

    def to_dict(self) -> dict:
        return {"id": self.id, "text": self.text, "start": self.start,
                "end": self.end, "parent_id": self.parent_id, "level": self.level}


class RecursiveChunker:
    """Split text into chunks recursively by structure."""

    SEPARATORS = ["\n\n\n", "\n\n", "\n", ". ", " ! ", " ? ", " "]
    DEFAULT_CHUNK_SIZE = 500
    DEFAULT_OVERLAP = 50

    def __init__(self, chunk_size: int = None, overlap: int = None, min_chunk: int = 100):
        self.chunk_size = chunk_size or self.DEFAULT_CHUNK_SIZE
        self.overlap = overlap or self.DEFAULT_OVERLAP
        self.min_chunk = min_chunk
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"c{self._counter}"

    def _split(self, text: str, sep: str) -> list[str]:
        parts = text.split(sep)
        return [p for p in parts if p.strip()]

    def _fixed_split(self, text: str) -> list[str]:
        """Split text at character boundaries."""
        parts = []
        start = 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            # Try to break at a word boundary near end.
            while end > start and not text[end - 1].isspace():
                end -= 1
            if end == start:
                end = start + self.chunk_size
            parts.append(text[start:end])
            start = end
        return parts

    def chunk(self, text: str, sep_index: int = 0) -> list[Chunk]:
        """Recursively chunk text."""
        if sep_index >= len(self.SEPARATORS) or len(text) <= self.chunk_size:
            parts = self._fixed_split(text) if len(text) > self.chunk_size else [text]
            chunks = []
            for i, part in enumerate(parts):
                if len(part) < self.min_chunk:
                    continue
                chunks.append(Chunk(id=self._next_id(), text=part,
                                    start=sum(len(c.text) for c in chunks), end=sum(len(c.text) for c in chunks) + len(part)))
            return chunks
        parts = self._split(text, self.SEPARATORS[sep_index])
        chunks = []
        if len(parts) == 1 and len(text) > self.chunk_size:
            # No separator found at this level, fall back.
            return self.chunk(text, sep_index + 1)
        combined = []
        for part in parts:
            combined.append(part)
            if len("\n".join(combined)) >= self.chunk_size:
                joined = "\n".join(combined[:-1])
                if len(joined) >= self.min_chunk:
                    chunks.append(Chunk(id=self._next_id(), text=joined))
                combined = [combined[-1]]
        if combined:
            joined = "\n".join(combined)
            if len(joined) >= self.min_chunk:
                chunks.append(Chunk(id=self._next_id(), text=joined))
        return chunks

    def chunk_with_overlap(self, text: str) -> list[Chunk]:
        """Chunk with overlap between adjacent chunks."""
        chunks = self.chunk(text)
        out = []
        for i, c in enumerate(chunks):
            if i > 0:
                prev = chunks[i - 1]
                overlap = c.text[:self.overlap]
                c = Chunk(id=c.id, text=overlap + c.text, start=c.start, end=c.end, parent_id=c.parent_id, level=c.level)
            out.append(c)
        return out

    def count_chunks(self, text: str) -> int:
        """Estimate chunk count for a text."""
        base = math.ceil(len(text) / self.chunk_size)
        return max(1, base)
