"""Chunking strategies for RAG pipelines."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    id: str
    document_id: str
    content: str
    chunk_index: int
    section: str = ""
    section_index: int = -1
    char_start: int = 0
    char_end: int = 0
    token_estimate: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    parent_id: Optional[str] = None


class ChunkingStrategies:
    """Multiple chunking strategies: semantic, paragraph, sliding, recursive."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, text: str, document_id: str, strategy: str = "semantic",
              sections: Optional[List[Dict[str, Any]]] = None) -> List[Chunk]:
        if not text or not text.strip():
            return []
        strategy = strategy.lower()
        if strategy == "section":
            return self._chunk_by_section(text, document_id, sections or [])
        if strategy == "paragraph":
            return self._chunk_by_paragraph(text, document_id)
        if strategy == "sentence":
            return self._chunk_by_sentence(text, document_id)
        if strategy == "sliding":
            return self._chunk_sliding(text, document_id)
        if strategy == "recursive":
            return self._chunk_recursive(text, document_id)
        return self._chunk_semantic(text, document_id, sections or [])

    def _chunk_by_section(self, text: str, document_id: str, sections: List[Dict[str, Any]]) -> List[Chunk]:
        if not sections:
            return self._chunk_semantic(text, document_id, [])
        lines = text.splitlines(keepends=True)
        chunks: List[Chunk] = []
        chunk_index = 0
        for idx, section in enumerate(sections):
            start = section.get("line", 0)
            end = sections[idx + 1].get("line", len(lines)) if idx + 1 < len(sections) else len(lines)
            section_text = "".join(lines[start:end]).strip()
            if not section_text:
                continue
            sub_chunks = self._chunk_semantic(section_text, document_id, [{"line": 0, "title": section.get("title", ""), "level": section.get("level", 1)}])
            for sub in sub_chunks:
                sub.section = section.get("title", "")
                sub.section_index = idx
                sub.id = self._make_id(document_id, chunk_index)
                sub.chunk_index = chunk_index
                chunks.append(sub)
                chunk_index += 1
        return chunks or self._chunk_semantic(text, document_id, [])

    def _chunk_by_paragraph(self, text: str, document_id: str) -> List[Chunk]:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks: List[Chunk] = []
        buffer: List[str] = []
        buffer_len = 0
        chunk_index = 0
        for para in paragraphs:
            if buffer_len + len(para) > self.chunk_size and buffer:
                content = "\n\n".join(buffer)
                chunks.append(Chunk(id=self._make_id(document_id, chunk_index), document_id=document_id,
                                    content=content, chunk_index=chunk_index,
                                    char_end=len(content), token_estimate=max(1, len(content.split()))))
                chunk_index += 1
                buffer = [buffer[-1]] if buffer else []
                buffer_len = sum(len(p) for p in buffer)
            buffer.append(para)
            buffer_len += len(para)
        if buffer:
            content = "\n\n".join(buffer)
            chunks.append(Chunk(id=self._make_id(document_id, chunk_index), document_id=document_id,
                                content=content, chunk_index=chunk_index,
                                char_end=len(content), token_estimate=max(1, len(content.split()))))
        return chunks

    def _chunk_by_sentence(self, text: str, document_id: str) -> List[Chunk]:
        sentences = self._split_sentences(text)
        chunks: List[Chunk] = []
        chunk_index = 0
        step = max(1, self.chunk_size // 100)
        for i in range(0, len(sentences), step):
            content = " ".join(sentences[i:i + step])
            if content.strip():
                chunk = Chunk(id=self._make_id(document_id, chunk_index), document_id=document_id,
                              content=content, chunk_index=chunk_index,
                              char_end=len(content), token_estimate=max(1, len(content.split())))
                chunks.append(chunk)
                chunk_index += 1
        return chunks

    def _chunk_sliding(self, text: str, document_id: str) -> List[Chunk]:
        chunks: List[Chunk] = []
        step = max(1, self.chunk_size - self.chunk_overlap)
        for i in range(0, len(text), step):
            content = text[i:i + self.chunk_size]
            if content.strip():
                chunk = Chunk(id=self._make_id(document_id, len(chunks)), document_id=document_id,
                              content=content, chunk_index=len(chunks),
                              char_start=i, char_end=i + len(content),
                              token_estimate=max(1, len(content.split())))
                chunks.append(chunk)
        return chunks

    def _chunk_recursive(self, text: str, document_id: str) -> List[Chunk]:
        separators = ["\n\n", "\n", ". ", " "]
        return self._recursive_split(text, document_id, separators, 0)

    def _recursive_split(self, text: str, document_id: str,
                         separators: List[str], depth: int) -> List[Chunk]:
        if len(text) <= self.chunk_size or depth >= len(separators):
            if text.strip():
                return [Chunk(id=self._make_id(document_id, 0), document_id=document_id,
                              content=text.strip(), chunk_index=0,
                              token_estimate=max(1, len(text.split())))]
            return []
        sep = separators[depth]
        parts = text.split(sep)
        chunks: List[Chunk] = []
        current = ""
        chunk_index = 0
        for part in parts:
            if len(current) + len(sep) + len(part) > self.chunk_size and current:
                sub = self._recursive_split(current, document_id, separators, depth + 1)
                for s in sub:
                    s.id = self._make_id(document_id, chunk_index)
                    s.chunk_index = chunk_index
                    chunks.append(s)
                    chunk_index += 1
                current = part
            else:
                current = current + sep + part if current else part
        if current.strip():
            sub = self._recursive_split(current, document_id, separators, depth + 1)
            for s in sub:
                s.id = self._make_id(document_id, chunk_index)
                s.chunk_index = chunk_index
                chunks.append(s)
                chunk_index += 1
        return chunks

    def _chunk_semantic(self, text: str, document_id: str,
                        sections: List[Dict[str, Any]]) -> List[Chunk]:
        sentences = self._split_sentences(text)
        if not sentences:
            return []
        chunks: List[Chunk] = []
        current: List[str] = []
        current_len = 0
        char_pos = 0
        chunk_index = 0
        for sentence in sentences:
            sentence_len = len(sentence)
            if current_len + sentence_len > self.chunk_size and current:
                content = " ".join(current)
                section, sidx = self._locate_section(char_pos, sections)
                chunks.append(Chunk(id=self._make_id(document_id, chunk_index), document_id=document_id,
                                    content=content, chunk_index=chunk_index, section=section,
                                    section_index=sidx, char_start=char_pos,
                                    char_end=char_pos + len(content),
                                    token_estimate=max(1, len(content.split()))))
                chunk_index += 1
                overlap = self._take_overlap(current)
                char_pos += max(0, len(content) - len(overlap))
                current = overlap
                current_len = sum(len(s) for s in current)
            current.append(sentence)
            current_len += sentence_len
        if current:
            content = " ".join(current)
            section, sidx = self._locate_section(char_pos, sections)
            chunks.append(Chunk(id=self._make_id(document_id, chunk_index), document_id=document_id,
                                content=content, chunk_index=chunk_index, section=section,
                                section_index=sidx, char_start=char_pos,
                                char_end=char_pos + len(content),
                                token_estimate=max(1, len(content.split()))))
        return chunks

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        parts = re.split(r"(?<=[.!?])\s+", text)
        return [p.strip() for p in parts if p.strip()]

    @staticmethod
    def _locate_section(char_pos: int, sections: List[Dict[str, Any]]) -> Tuple[str, int]:
        if not sections:
            return "", -1
        return sections[-1].get("title", ""), -1

    @staticmethod
    def _take_overlap(sentences: List[str]) -> List[str]:
        total = sum(len(s) for s in sentences)
        if total == 0:
            return []
        result: List[str] = []
        running = 0
        target = max(1, total // 6)
        for sentence in reversed(sentences):
            if running >= target:
                break
            result.insert(0, sentence)
            running += len(sentence)
        return result

    @staticmethod
    def _make_id(document_id: str, index: int) -> str:
        return f"{document_id}_chunk_{index}"

    def tune(self, text_length: int) -> Tuple[int, int]:
        if text_length < 2000:
            return 300, 30
        if text_length < 20000:
            return 500, 50
        if text_length < 100000:
            return 800, 100
        return 1200, 150
