"""Advanced Document Intelligence — Stage 21 Step 4.

Provides:
- Multi-format document parsing (PDF, DOCX, Markdown, TXT, CSV, Excel)
- OCR processing (simulated heuristics for scanned documents)
- Intelligent chunking with semantic boundaries, section detection, overlap tuning
- Metadata extraction (author, title, dates, language, word count, reading time, keywords)
- AI summarization (extractive and abstractive), section summaries, key points
- Citation generation in multiple styles (APA, MLA, Chicago, IEEE)
- Near-duplicate detection via SimHash, MinHash, fuzzy matching, fingerprinting

All parsers are abstracted so they can be swapped with real libraries
(PyPDF2, python-docx, openpyxl, pytesseract, etc.) without breaking the API.
"""

import csv
import hashlib
import io
import logging
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from io import StringIO
from typing import Optional

logger = logging.getLogger(__name__)


SUPPORTED_FORMATS = {
    "pdf": {"extensions": [".pdf"], "mime": "application/pdf", "parser": "pdf"},
    "docx": {"extensions": [".docx"], "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "parser": "docx"},
    "md": {"extensions": [".md", ".markdown"], "mime": "text/markdown", "parser": "markdown"},
    "txt": {"extensions": [".txt"], "mime": "text/plain", "parser": "text"},
    "csv": {"extensions": [".csv"], "mime": "text/csv", "parser": "csv"},
    "xlsx": {"extensions": [".xlsx"], "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "parser": "excel"},
}

LANGUAGE_KEYWORDS = {
    "en": {"the", "and", "is", "of", "to", "in", "that", "for", "with", "as"},
    "es": {"el", "la", "de", "que", "y", "en", "un", "una", "por", "para"},
    "fr": {"le", "de", "un", "une", "et", "à", "en", "que", "pour", "avec"},
    "de": {"der", "die", "das", "und", "ist", "von", "mit", "nicht", "sich", "auf"},
    "it": {"il", "di", "che", "è", "un", "una", "per", "con", "non", "sono"},
}


@dataclass
class ParsedDocument:
    """A parsed document with extracted text and structure."""
    text: str
    format: str
    sections: list[dict] = field(default_factory=list)
    tables: list[dict] = field(default_factory=list)
    images: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    page_count: int = 0
    word_count: int = 0
    char_count: int = 0
    parse_time_ms: float = 0.0


@dataclass
class Chunk:
    """An intelligent chunk of a document."""
    id: str
    document_id: str
    content: str
    chunk_index: int
    section: str = ""
    section_index: int = -1
    char_start: int = 0
    char_end: int = 0
    token_estimate: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class DocumentMetadata:
    """Extracted document metadata."""
    title: str = ""
    author: str = ""
    subject: str = ""
    keywords: list[str] = field(default_factory=list)
    creation_date: str = ""
    modification_date: str = ""
    language: str = "en"
    word_count: int = 0
    char_count: int = 0
    sentence_count: int = 0
    paragraph_count: int = 0
    reading_time_minutes: float = 0.0
    page_count: int = 0
    summary: str = ""
    format: str = ""


@dataclass
class Citation:
    """A generated citation."""
    style: str
    text: str
    authors: list[str] = field(default_factory=list)
    title: str = ""
    year: str = ""
    source: str = ""
    url: str = ""


@dataclass
class DuplicateMatch:
    """A duplicate document match."""
    document_id: str
    similarity: float
    match_type: str  # exact, near, fuzzy
    fingerprint_distance: int = 0


class DocumentParser:
    """Parse documents of various formats into structured text."""

    def parse(self, content: bytes, filename: str, format_hint: Optional[str] = None) -> ParsedDocument:
        """Parse a document. ``content`` is raw bytes; ``filename`` used for format detection."""
        start = time.time()
        fmt = format_hint or self._detect_format(filename, content)

        text = ""
        sections: list[dict] = []
        tables: list[dict] = []
        images: list[dict] = []
        metadata: dict = {}
        page_count = 0

        try:
            if fmt == "pdf":
                text, page_count, metadata = self._parse_pdf(content)
            elif fmt == "docx":
                text, metadata = self._parse_docx(content)
            elif fmt == "markdown":
                text, sections = self._parse_markdown(content)
            elif fmt == "csv":
                text, tables = self._parse_csv(content)
            elif fmt == "excel":
                text, tables = self._parse_excel(content)
            else:
                text = self._parse_text(content)
        except Exception as exc:
            logger.warning("Parser failed for %s (%s): %s", filename, fmt, exc)
            text = self._parse_text(content)
            fmt = "txt"

        word_count = len(text.split()) if text else 0
        elapsed_ms = (time.time() - start) * 1000

        return ParsedDocument(
            text=text,
            format=fmt,
            sections=sections,
            tables=tables,
            images=images,
            metadata=metadata,
            page_count=page_count,
            word_count=word_count,
            char_count=len(text),
            parse_time_ms=round(elapsed_ms, 3),
        )

    @staticmethod
    def _detect_format(filename: str, content: bytes) -> str:
        name = (filename or "").lower()
        for fmt, info in SUPPORTED_FORMATS.items():
            if any(name.endswith(ext) for ext in info["extensions"]):
                return fmt
        if content.startswith(b"%PDF-"):
            return "pdf"
        if content[:2] == b"PK" and b"word" in content[:200].lower():
            return "docx"
        return "txt"

    @staticmethod
    def _parse_text(content: bytes) -> str:
        try:
            return content.decode("utf-8", errors="ignore")
        except Exception:
            return content.decode("latin-1", errors="ignore")

    @staticmethod
    def _parse_pdf(content: bytes) -> tuple[str, int, dict]:
        """Parse PDF. In production: PyPDF2/pypdf. Here we simulate."""
        text = content.decode("latin-1", errors="ignore")
        readable = re.findall(r"\(([^)]+)\)\s*Tj", text)
        joined = " ".join(readable).strip()
        if not joined:
            joined = re.sub(r"[^\x20-\x7E\n]+", " ", text).strip()
        page_count = max(1, text.count("/Type /Page") - text.count("/Type /Pages"))
        metadata = {}
        title_match = re.search(r"/Title\s*\(([^)]+)\)", text)
        author_match = re.search(r"/Author\s*\(([^)]+)\)", text)
        if title_match:
            metadata["title"] = title_match.group(1).strip()
        if author_match:
            metadata["author"] = author_match.group(1).strip()
        return joined or "[PDF content extracted]", page_count, metadata

    @staticmethod
    def _parse_docx(content: bytes) -> tuple[str, dict]:
        """Parse DOCX. In production: python-docx. Here we simulate."""
        text = content.decode("latin-1", errors="ignore")
        body_match = re.search(r"<w:body>(.*?)</w:body>", text, re.DOTALL)
        body = body_match.group(1) if body_match else text
        paragraphs = re.findall(r"<w:t[^>]*>([^<]+)</w:t>", body)
        joined = " ".join(paragraphs).strip() or "[DOCX content extracted]"
        metadata = {}
        title_match = re.search(r"<dc:title>([^<]+)</dc:title>", text)
        author_match = re.search(r"<dc:creator>([^<]+)</dc:creator>", text)
        if title_match:
            metadata["title"] = title_match.group(1).strip()
        if author_match:
            metadata["author"] = author_match.group(1).strip()
        return joined, metadata

    @staticmethod
    def _parse_markdown(content: bytes) -> tuple[str, list[dict]]:
        text = content.decode("utf-8", errors="ignore")
        sections: list[dict] = []
        for idx, line in enumerate(text.splitlines()):
            m = re.match(r"^(#{1,6})\s+(.+)$", line)
            if m:
                sections.append({"level": len(m.group(1)), "title": m.group(2).strip(), "line": idx})
        return text, sections

    @staticmethod
    def _parse_csv(content: bytes) -> tuple[str, list[dict]]:
        text = content.decode("utf-8", errors="ignore")
        tables: list[dict] = []
        try:
            reader = csv.reader(StringIO(text))
            rows = [row for row in reader if row]
            if rows:
                tables.append({"headers": rows[0], "rows": rows[1:], "row_count": len(rows) - 1})
        except Exception:
            pass
        return text, tables

    @staticmethod
    def _parse_excel(content: bytes) -> tuple[str, list[dict]]:
        """Parse Excel. In production: openpyxl. Here we simulate."""
        text = content.decode("latin-1", errors="ignore")
        tables = [{"headers": ["Column A", "Column B"], "rows": [["data", "data"]], "row_count": 1, "note": "simulated"}]
        return "[Excel content extracted]\n" + text[:500], tables


class OCRProcessor:
    """OCR for scanned documents.

    In production this would call Tesseract or a cloud OCR API.
    Here we use heuristic text extraction from images — identifying
    potential text regions, cleaning noise, and extracting readable runs.
    """

    def __init__(self):
        self.confidence_threshold = 0.5

    def process(self, image_bytes: bytes, filename: str = "") -> dict:
        """Run OCR on image bytes."""
        start = time.time()
        text_runs = self._extract_text_runs(image_bytes)
        full_text = " ".join(text_runs)
        confidence = self._estimate_confidence(image_bytes, full_text)

        elapsed = (time.time() - start) * 1000
        return {
            "text": full_text,
            "confidence": round(confidence, 3),
            "regions": [{"text": t, "confidence": confidence} for t in text_runs],
            "language": "en",
            "engine": "simulated_heuristic",
            "note": "Real OCR requires Tesseract or cloud API integration",
            "processing_time_ms": round(elapsed, 3),
            "filename": filename,
            "word_count": len(full_text.split()),
        }

    @staticmethod
    def _extract_text_runs(image_bytes: bytes) -> list[str]:
        """Simulated extraction of textual runs from bytes."""
        if not image_bytes:
            return []
        sample = image_bytes[:1024]
        ascii_chunks = re.findall(rb"[\x20-\x7E]{6,}", sample)
        return [chunk.decode("ascii", errors="ignore") for chunk in ascii_chunks if len(chunk) >= 6]

    @staticmethod
    def _estimate_confidence(image_bytes: bytes, extracted_text: str) -> float:
        if not image_bytes:
            return 0.0
        size_factor = min(1.0, len(image_bytes) / 50000)
        text_factor = min(1.0, len(extracted_text) / 500)
        return round(0.3 + 0.5 * size_factor + 0.2 * text_factor, 3)


class MetadataExtractor:
    """Extract rich metadata from text content."""

    STOPWORDS = {
        "the", "and", "is", "of", "to", "in", "that", "for", "with", "as", "on",
        "at", "by", "an", "a", "be", "this", "it", "from", "or", "are", "was",
        "were", "but", "not", "have", "has", "had", "they", "their", "we", "you",
        "i", "he", "she", "his", "her", "its", "our", "your", "my", "me", "us",
        "them", "what", "which", "who", "when", "where", "why", "how", "all",
        "any", "both", "each", "few", "more", "most", "other", "some", "such",
        "than", "too", "very", "can", "will", "just", "into", "out", "up",
    }

    READING_WPM = 200

    def extract(self, text: str, parsed: Optional[ParsedDocument] = None) -> DocumentMetadata:
        meta = DocumentMetadata()
        if not text:
            return meta

        meta.format = parsed.format if parsed else "txt"
        meta.word_count = len(text.split())
        meta.char_count = len(text)
        meta.sentence_count = max(1, len(re.findall(r"[.!?]+", text)))
        meta.paragraph_count = max(1, len([p for p in text.split("\n\n") if p.strip()]))
        meta.reading_time_minutes = round(meta.word_count / self.READING_WPM, 2)
        meta.page_count = max(1, meta.word_count // 250)
        meta.language = self._detect_language(text)
        meta.title = self._extract_title(text, parsed)
        meta.author = (parsed.metadata.get("author") if parsed else "") or self._extract_author(text)
        meta.subject = self._extract_subject(text)
        meta.keywords = self._extract_keywords(text)
        meta.summary = self._quick_summary(text)

        if parsed:
            creation = parsed.metadata.get("creation_date")
            if creation:
                meta.creation_date = creation
            mod = parsed.metadata.get("modification_date")
            if mod:
                meta.modification_date = mod

        return meta

    @staticmethod
    def _detect_language(text: str) -> str:
        words = set(re.findall(r"\b[a-zà-ÿ]{2,}\b", text.lower()))
        if not words:
            return "en"
        scores = {}
        for lang, keywords in LANGUAGE_KEYWORDS.items():
            scores[lang] = len(words & keywords)
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "en"

    @staticmethod
    def _extract_title(text: str, parsed: Optional[ParsedDocument]) -> str:
        if parsed and parsed.metadata.get("title"):
            return parsed.metadata["title"]
        if parsed and parsed.sections:
            for section in parsed.sections:
                if section["level"] == 1:
                    return section["title"]
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if lines:
            first = lines[0]
            if len(first) <= 120 and not first.endswith("."):
                return first
        return "Untitled Document"

    @staticmethod
    def _extract_author(text: str) -> str:
        match = re.search(r"(?:by|author|written by)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})", text, re.IGNORECASE)
        return match.group(1).strip() if match else ""

    @staticmethod
    def _extract_subject(text: str) -> str:
        sentences = re.split(r"(?<=[.!?])\s+", text[:1000])
        if sentences:
            return sentences[0][:200]
        return ""

    def _extract_keywords(self, text: str, max_keywords: int = 10) -> list[str]:
        words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
        filtered = [w for w in words if w not in self.STOPWORDS]
        counts = Counter(filtered)
        return [word for word, _ in counts.most_common(max_keywords)]

    @staticmethod
    def _quick_summary(text: str, max_sentences: int = 2) -> str:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        return " ".join(sentences[:max_sentences])[:500]


class IntelligentChunker:
    """Chunk documents by semantic boundaries with overlap tuning."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50, strategy: str = "semantic"):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.strategy = strategy  # semantic | sentence | paragraph | section

    def chunk(
        self,
        text: str,
        document_id: str,
        sections: Optional[list[dict]] = None,
    ) -> list[Chunk]:
        """Split ``text`` into semantic chunks."""
        if not text or not text.strip():
            return []

        if self.strategy == "section" and sections:
            return self._chunk_by_section(text, document_id, sections)
        if self.strategy == "paragraph":
            return self._chunk_by_paragraph(text, document_id)
        return self._chunk_semantic(text, document_id, sections or [])

    def _chunk_semantic(self, text: str, document_id: str, sections: list[dict]) -> list[Chunk]:
        sentences = self._split_sentences(text)
        if not sentences:
            return []

        chunks: list[Chunk] = []
        current: list[str] = []
        current_len = 0
        char_pos = 0
        chunk_index = 0

        for sentence in sentences:
            sentence_len = len(sentence)
            if current_len + sentence_len > self.chunk_size and current:
                content = " ".join(current)
                section, sidx = self._locate_section(char_pos, sections)
                chunk_id = self._make_id(document_id, chunk_index)
                chunks.append(Chunk(
                    id=chunk_id,
                    document_id=document_id,
                    content=content,
                    chunk_index=chunk_index,
                    section=section,
                    section_index=sidx,
                    char_start=char_pos,
                    char_end=char_pos + len(content),
                    token_estimate=max(1, len(content.split())),
                ))
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
            chunks.append(Chunk(
                id=self._make_id(document_id, chunk_index),
                document_id=document_id,
                content=content,
                chunk_index=chunk_index,
                section=section,
                section_index=sidx,
                char_start=char_pos,
                char_end=char_pos + len(content),
                token_estimate=max(1, len(content.split())),
            ))

        return chunks

    def _chunk_by_section(self, text: str, document_id: str, sections: list[dict]) -> list[Chunk]:
        lines = text.splitlines(keepends=True)
        chunks: list[Chunk] = []
        chunk_index = 0
        sorted_sections = sorted(sections, key=lambda s: s.get("line", 0))

        for idx, section in enumerate(sorted_sections):
            start_line = section.get("line", 0)
            end_line = sorted_sections[idx + 1]["line"] if idx + 1 < len(sorted_sections) else len(lines)
            section_content = "".join(lines[start_line:end_line]).strip()
            if not section_content:
                continue
            sub_chunks = self._chunk_semantic(
                section_content,
                document_id,
                [{"line": 0, "title": section["title"], "level": section["level"]}],
            )
            for sub in sub_chunks:
                sub.id = self._make_id(document_id, chunk_index)
                sub.chunk_index = chunk_index
                sub.section = section["title"]
                sub.section_index = idx
                chunks.append(sub)
                chunk_index += 1

        if not chunks:
            chunks = self._chunk_semantic(text, document_id, [])
        return chunks

    def _chunk_by_paragraph(self, text: str, document_id: str) -> list[Chunk]:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks: list[Chunk] = []
        buffer: list[str] = []
        buffer_len = 0
        chunk_index = 0

        for para in paragraphs:
            if buffer_len + len(para) > self.chunk_size and buffer:
                content = "\n\n".join(buffer)
                chunks.append(Chunk(
                    id=self._make_id(document_id, chunk_index),
                    document_id=document_id,
                    content=content,
                    chunk_index=chunk_index,
                    char_end=len(content),
                    token_estimate=max(1, len(content.split())),
                ))
                chunk_index += 1
                buffer = [buffer[-1]] if buffer else []
                buffer_len = sum(len(p) for p in buffer)
            buffer.append(para)
            buffer_len += len(para)

        if buffer:
            content = "\n\n".join(buffer)
            chunks.append(Chunk(
                id=self._make_id(document_id, chunk_index),
                document_id=document_id,
                content=content,
                chunk_index=chunk_index,
                char_end=len(content),
                token_estimate=max(1, len(content.split())),
            ))
        return chunks

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        parts = re.split(r"(?<=[.!?])\s+", text)
        return [p.strip() for p in parts if p.strip()]

    @staticmethod
    def _locate_section(char_pos: int, sections: list[dict]) -> tuple[str, int]:
        if not sections:
            return "", -1
        return sections[-1].get("title", ""), -1

    @staticmethod
    def _take_overlap(sentences: list[str]) -> list[str]:
        total = sum(len(s) for s in sentences)
        if total == 0:
            return []
        result: list[str] = []
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

    def tune_overlap(self, text_length: int) -> tuple[int, int]:
        """Return tuned (chunk_size, overlap) based on text length."""
        if text_length < 2000:
            return 300, 30
        if text_length < 20000:
            return 500, 50
        if text_length < 100000:
            return 800, 100
        return 1200, 150


class Summarizer:
    """AI-style summarization with extractive and abstractive modes."""

    STOPWORDS = MetadataExtractor.STOPWORDS

    def summarize(
        self,
        text: str,
        mode: str = "extractive",
        max_sentences: int = 3,
    ) -> dict:
        """Generate a summary of ``text``."""
        if not text or not text.strip():
            return {"summary": "", "sentences": [], "key_points": [], "mode": mode, "compression_ratio": 0.0}

        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        if not sentences:
            return {"summary": "", "sentences": [], "key_points": [], "mode": mode, "compression_ratio": 0.0}

        if mode == "abstractive":
            summary_text = self._abstractive_summary(sentences, max_sentences)
        else:
            summary_text = self._extractive_summary(sentences, max_sentences)

        key_points = self._extract_key_points(sentences, limit=5)
        section_summaries = self._section_summaries(text, max_sentences=2)
        compression = round(1 - len(summary_text) / max(len(text), 1), 3)

        return {
            "summary": summary_text,
            "sentences": summary_text.split(". ") if summary_text else [],
            "key_points": key_points,
            "section_summaries": section_summaries,
            "mode": mode,
            "compression_ratio": max(0.0, compression),
            "original_sentences": len(sentences),
            "summary_sentences": len(summary_text.split(". ")) if summary_text else 0,
        }

    def _extractive_summary(self, sentences: list[str], max_sentences: int) -> str:
        scores = self._score_sentences(sentences)
        ranked = sorted(enumerate(sentences), key=lambda x: scores[x[0]], reverse=True)
        keep = sorted(ranked[:max_sentences], key=lambda x: x[0])
        return " ".join(s for _, s in keep)

    def _abstractive_summary(self, sentences: list[str], max_sentences: int) -> str:
        """Simulated abstractive summary — paraphrases the top sentences."""
        scored = self._score_sentences(sentences)
        ranked_indices = sorted(range(len(sentences)), key=lambda i: scored[i], reverse=True)[:max_sentences]
        ranked_indices.sort()
        paraphrased = []
        for idx in ranked_indices:
            sentence = sentences[idx]
            words = sentence.split()
            if len(words) > 8:
                words = words[: max(6, len(words) - 2)]
            paraphrased.append("In summary, " + " ".join(words))
        return " ".join(paraphrased)

    def _score_sentences(self, sentences: list[str]) -> list[float]:
        word_freq = Counter()
        for sentence in sentences:
            for word in re.findall(r"\b[a-zA-Z]{3,}\b", sentence.lower()):
                if word not in self.STOPWORDS:
                    word_freq[word] += 1
        if not word_freq:
            return [0.0] * len(sentences)

        max_freq = max(word_freq.values())
        scores: list[float] = []
        for idx, sentence in enumerate(sentences):
            words = re.findall(r"\b[a-zA-Z]{3,}\b", sentence.lower())
            score = sum(word_freq.get(w, 0) for w in words) / max(1, len(words))
            if idx == 0:
                score *= 1.2  # lead bias
            scores.append(score / max_freq)
        return scores

    @staticmethod
    def _extract_key_points(sentences: list[str], limit: int = 5) -> list[str]:
        if not sentences:
            return []
        scored = []
        for s in sentences:
            words = re.findall(r"\b[a-zA-Z]{4,}\b", s)
            scored.append((len(set(words)), s))
        scored.sort(reverse=True)
        return [s for _, s in scored[:limit]]

    @staticmethod
    def _section_summaries(text: str, max_sentences: int = 2) -> list[dict]:
        sections = []
        current = {"title": "Introduction", "lines": []}
        for line in text.splitlines():
            m = re.match(r"^(#{1,6})\s+(.+)$", line)
            if m:
                if current["lines"]:
                    sections.append(current)
                current = {"title": m.group(2).strip(), "lines": []}
            else:
                current["lines"].append(line)
        if current["lines"]:
            sections.append(current)

        result = []
        for section in sections:
            content = " ".join(line.strip() for line in section["lines"] if line.strip())
            sentences = re.split(r"(?<=[.!?])\s+", content)
            summary = " ".join(sentences[:max_sentences]).strip()
            result.append({"title": section["title"], "summary": summary[:500]})
        return result or [{"title": "Full Document", "summary": text[:500]}]


class CitationGenerator:
    """Generate citations in multiple academic styles."""

    STYLES = ("apa", "mla", "chicago", "ieee")

    @staticmethod
    def extract_references(text: str) -> list[dict]:
        """Extract reference-like patterns from document text."""
        references: list[dict] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            year_match = re.search(r"\b(19|20)\d{2}\b", line)
            author_match = re.match(r"([A-Z][a-z]+(?:\s+[A-Z]\.?)*(?:\s*,?\s*(?:&|and)\s*[A-Z][a-z]+)*)", line)
            if year_match and author_match and len(line) > 30:
                references.append({
                    "raw": line,
                    "authors": [author_match.group(1).strip()],
                    "year": year_match.group(0),
                    "title": line[:120],
                })
            url_match = re.search(r"https?://[^\s)]+", line)
            if url_match and len(line) > 15:
                references.append({"raw": line, "url": url_match.group(0)})
        return references

    def generate(
        self,
        document_title: str,
        authors: list[str],
        year: Optional[str] = None,
        source: str = "",
        url: str = "",
        style: str = "apa",
    ) -> Citation:
        """Generate a citation in the requested style."""
        year = year or str(time.localtime().tm_year)
        style = style.lower() if style else "apa"
        if style not in self.STYLES:
            style = "apa"

        if style == "apa":
            text = self._apa(authors, year, document_title, source, url)
        elif style == "mla":
            text = self._mla(authors, document_title, source, url)
        elif style == "chicago":
            text = self._chicago(authors, year, document_title, source, url)
        else:
            text = self._ieee(authors, document_title, year, source, url)

        return Citation(
            style=style,
            text=text,
            authors=authors,
            title=document_title,
            year=year,
            source=source,
            url=url,
        )

    @staticmethod
    def _apa(authors: list[str], year: str, title: str, source: str, url: str) -> str:
        author_str = ", ".join(authors) if authors else "Unknown Author"
        parts = [f"{author_str} ({year}).", f"{title}."]
        if source:
            parts.append(f"{source}.")
        if url:
            parts.append(url)
        return " ".join(parts)

    @staticmethod
    def _mla(authors: list[str], title: str, source: str, url: str) -> str:
        author_str = ", ".join(authors) if authors else "Unknown Author"
        parts = [f'{author_str}. "{title}."']
        if source:
            parts.append(f"{source},")
        if url:
            parts.append(url)
        parts.append(f'{time.strftime("%d %b. %Y")}.')
        return " ".join(parts)

    @staticmethod
    def _chicago(authors: list[str], year: str, title: str, source: str, url: str) -> str:
        author_str = ", ".join(authors) if authors else "Unknown Author"
        parts = [f'{author_str}. "{title}."']
        if source:
            parts.append(f"{source} ({year}).")
        else:
            parts.append(f"({year}).")
        if url:
            parts.append(url)
        return " ".join(parts)

    @staticmethod
    def _ieee(authors: list[str], title: str, year: str, source: str, url: str) -> str:
        author_str = ", ".join(authors) if authors else "Unknown Author"
        parts = [f'{author_str}, "{title},"']
        if source:
            parts.append(f"{source},")
        parts.append(f"{year}.")
        if url:
            parts.append(f"[Online]. Available: {url}")
        return " ".join(parts)

    def generate_from_document(self, text: str, default_style: str = "apa") -> list[Citation]:
        """Auto-generate citations from references found in text."""
        refs = self.extract_references(text)
        citations: list[Citation] = []
        for ref in refs:
            citations.append(self.generate(
                document_title=ref.get("title", ref.get("raw", "")[:80]),
                authors=ref.get("authors", []),
                year=ref.get("year"),
                url=ref.get("url", ""),
                style=default_style,
            ))
        return citations


class DuplicateDetector:
    """Detect near-duplicate documents via SimHash, MinHash, and shingling."""

    def __init__(self):
        self._fingerprints: dict[str, dict] = {}

    def register(self, document_id: str, text: str) -> dict:
        """Register a document and compute fingerprints."""
        fingerprint = {
            "simhash": self.simhash(text),
            "minhash": self.minhash(text),
            "shingles": self._shingles(text),
            "sha256": self._sha256(text),
            "length": len(text),
            "word_count": len(text.split()),
        }
        self._fingerprints[document_id] = fingerprint
        return fingerprint

    def find_duplicates(
        self,
        document_id: str,
        text: str,
        threshold: float = 0.85,
    ) -> list[DuplicateMatch]:
        """Find duplicate matches for ``document_id``/``text``."""
        source = self.register(document_id, text)
        matches: list[DuplicateMatch] = []

        for other_id, other_fp in self._fingerprints.items():
            if other_id == document_id:
                continue
            exact = source["sha256"] == other_fp["sha256"]
            if exact:
                matches.append(DuplicateMatch(other_id, 1.0, "exact"))
                continue
            jaccard = self._jaccard(source["shingles"], other_fp["shingles"])
            sim_dist = bin(source["simhash"] ^ other_fp["simhash"]).count("1")
            sim_sim = 1.0 - sim_dist / 64.0
            similarity = max(jaccard, sim_sim)
            if similarity >= threshold:
                match_type = "near" if similarity >= 0.95 else "fuzzy"
                matches.append(DuplicateMatch(other_id, round(similarity, 4), match_type, sim_dist))

        matches.sort(key=lambda m: m.similarity, reverse=True)
        return matches

    @staticmethod
    def simhash(text: str, hashbits: int = 64) -> int:
        """Compute a SimHash fingerprint of text."""
        text = text.lower()
        tokens = re.findall(r"\b\w+\b", text)
        if not tokens:
            return 0
        shingles = [" ".join(tokens[i:i + 3]) for i in range(len(tokens) - 2)] or tokens
        vector = [0] * hashbits
        for shingle in shingles:
            h = int(hashlib.md5(shingle.encode("utf-8", errors="ignore")).hexdigest()[:16], 16)
            for i in range(hashbits):
                if h & (1 << i):
                    vector[i] += 1
                else:
                    vector[i] -= 1
        fingerprint = 0
        for i, v in enumerate(vector):
            if v > 0:
                fingerprint |= 1 << i
        return fingerprint

    @staticmethod
    def minhash(text: str, num_hashes: int = 128) -> list[int]:
        """Compute a MinHash signature for text."""
        text = text.lower()
        tokens = re.findall(r"\b\w+\b", text)
        if not tokens:
            return [0] * num_hashes
        shingles = {" ".join(tokens[i:i + 3]) for i in range(len(tokens) - 2)} or set(tokens)
        if not shingles:
            return [0] * num_hashes
        signature: list[int] = []
        for i in range(num_hashes):
            min_hash = min(
                int(hashlib.md5(f"{i}_{shingle}".encode("utf-8", errors="ignore")).hexdigest()[:8], 16)
                for shingle in shingles
            )
            signature.append(min_hash)
        return signature

    @staticmethod
    def _shingles(text: str, k: int = 5) -> set[int]:
        text = re.sub(r"\s+", " ", text.lower()).strip()
        if len(text) < k:
            return {hash(text)}
        return {hash(text[i:i + k]) for i in range(len(text) - k + 1)}

    @staticmethod
    def _sha256(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()

    @staticmethod
    def _jaccard(a: set[int], b: set[int]) -> float:
        if not a or not b:
            return 0.0
        intersection = len(a & b)
        union = len(a | b)
        return intersection / union if union else 0.0

    def minhash_similarity(self, sig_a: list[int], sig_b: list[int]) -> float:
        if not sig_a or not sig_b or len(sig_a) != len(sig_b):
            return 0.0
        return sum(1 for a, b in zip(sig_a, sig_b) if a == b) / len(sig_a)

    def fingerprint(self, text: str) -> dict:
        """Convenience wrapper returning all fingerprints for ``text``."""
        return {
            "simhash": self.simhash(text),
            "minhash": self.minhash(text),
            "sha256": self._sha256(text),
            "length": len(text),
        }

    def clear(self):
        self._fingerprints.clear()


class DocumentIntelligence:
    """Top-level orchestrator that exposes all intelligence features."""

    def __init__(self):
        self.parser = DocumentParser()
        self.ocr = OCRProcessor()
        self.metadata_extractor = MetadataExtractor()
        self.chunker = IntelligentChunker()
        self.summarizer = Summarizer()
        self.citations = CitationGenerator()
        self.duplicate_detector = DuplicateDetector()
        self._documents: dict[str, dict] = {}

    def process(self, content: bytes, filename: str, user_id: str = "") -> dict:
        """Run the full intelligence pipeline on a document."""
        parsed = self.parser.parse(content, filename)
        metadata = self.metadata_extractor.extract(parsed.text, parsed)
        chunks = self.chunker.chunk(parsed.text, document_id=filename, sections=parsed.sections)
        summary = self.summarizer.summarize(parsed.text)
        citations = self.citations.generate_from_document(parsed.text)
        fingerprint = self.duplicate_detector.fingerprint(parsed.text)
        duplicates = self.duplicate_detector.find_duplicates(filename, parsed.text)

        import secrets
        doc_id = secrets.token_hex(8)
        record = {
            "id": doc_id,
            "user_id": user_id,
            "filename": filename,
            "format": parsed.format,
            "parsed": parsed,
            "metadata": metadata,
            "chunks": chunks,
            "summary": summary,
            "citations": citations,
            "fingerprint": fingerprint,
            "duplicates": duplicates,
            "created_at": time.time(),
        }
        self._documents[doc_id] = record
        return self._to_response(record)

    def get(self, doc_id: str) -> Optional[dict]:
        record = self._documents.get(doc_id)
        return self._to_response(record) if record else None

    def list_documents(self) -> list[dict]:
        return [
            {
                "id": rec["id"],
                "filename": rec["filename"],
                "format": rec["format"],
                "created_at": rec["created_at"],
            }
            for rec in self._documents.values()
        ]

    @staticmethod
    def _to_response(record: dict) -> dict:
        parsed: ParsedDocument = record["parsed"]
        metadata: DocumentMetadata = record["metadata"]
        return {
            "id": record["id"],
            "filename": record["filename"],
            "format": record["format"],
            "user_id": record["user_id"],
            "created_at": record["created_at"],
            "text_length": parsed.char_count,
            "word_count": metadata.word_count,
            "page_count": metadata.page_count or parsed.page_count,
            "sections": parsed.sections,
            "tables": parsed.tables,
            "metadata": {
                "title": metadata.title,
                "author": metadata.author,
                "subject": metadata.subject,
                "keywords": metadata.keywords,
                "language": metadata.language,
                "word_count": metadata.word_count,
                "char_count": metadata.char_count,
                "sentence_count": metadata.sentence_count,
                "paragraph_count": metadata.paragraph_count,
                "reading_time_minutes": metadata.reading_time_minutes,
                "summary": metadata.summary,
            },
            "chunks": [
                {
                    "id": c.id,
                    "chunk_index": c.chunk_index,
                    "content": c.content,
                    "section": c.section,
                    "token_estimate": c.token_estimate,
                }
                for c in record["chunks"]
            ],
            "chunk_count": len(record["chunks"]),
            "summary": record["summary"],
            "citations": [
                {"style": c.style, "text": c.text, "title": c.title, "year": c.year}
                for c in record["citations"]
            ],
            "fingerprint": record["fingerprint"],
            "duplicates": [
                {"document_id": m.document_id, "similarity": m.similarity, "match_type": m.match_type}
                for m in record["duplicates"]
            ],
        }


document_intelligence = DocumentIntelligence()