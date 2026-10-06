from scripts.phases._shared import write_module

# ============ PHASE 43 - RAG Engine ============

def build_phase_43_document_loader() -> str:
    """Unified document loading interface."""
    code = '''"""Unified document loader for multiple file formats."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator


@dataclass
class Document:
    """A loaded document with its content and metadata."""
    id: str
    text: str
    metadata: dict = field(default_factory=dict)
    path: str = ""
    page_count: int = 1

    def summary(self) -> str:
        words = self.text.split()
        if len(words) <= 100:
            return self.text
        return " ".join(words[:100]) + "..."

    def to_dict(self) -> dict:
        return {"id": self.id, "text": self.text[:1000], "metadata": self.metadata,
                "path": self.path, "page_count": self.page_count}


class DocumentLoader:
    """Unified loader for documents of various formats."""

    def __init__(self, supported: list[str] | None = None):
        self.supported = supported or ["txt", "md", "pdf", "docx"]
        self._loaded: list[Document] = []

    def _default_parser(self, path: Path) -> str:
        return path.read_text(encoding="utf-8", errors="replace")

    def load(self, path: str | Path, doc_type: str | None = None) -> Document:
        """Load a single document."""
        path = Path(path)
        doc_type = doc_type or path.suffix.lower().lstrip(".")
        text = self._default_parser(path)
        doc = Document(id=path.name, text=text, metadata={"source": str(path)}, path=str(path))
        self._loaded.append(doc)
        return doc

    def load_many(self, paths: list[str | Path], doc_type: str | None = None) -> list[Document]:
        """Load multiple documents."""
        return [self.load(p, doc_type) for p in paths]

    def load_dir(self, directory: str, pattern: str = "*") -> list[Document]:
        """Load all matching documents in a directory."""
        paths = list(Path(directory).glob(pattern))
        return self.load_many(paths)

    def iter_docs(self, paths: list[str | Path]) -> Iterator[Document]:
        """Iterate over documents as they load."""
        for p in paths:
            yield self.load(p)

    def get(self, doc_id: str) -> Document | None:
        return next((d for d in self._loaded if d.id == doc_id), None)

    def clear(self) -> None:
        self._loaded.clear()

    def supported_formats(self) -> list[str]:
        return list(self.supported)
'''
    write_module("43_document_loader", code)
    return "module: astrovox/phases/phase43_document_loader.py"


def build_phase_43_pdf_parser() -> str:
    """PDF text extraction."""
    code = '''"""PDF document parser using a fallback extraction strategy."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator


@dataclass
class PDFPage:
    """A single page from a PDF document."""
    page_num: int
    text: str
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"page_num": self.page_num, "text": self.text, "metadata": self.metadata}


@dataclass
class PDFDocument:
    """A parsed PDF document."""
    path: str
    pages: list[PDFPage] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    page_count: int = 0

    def to_text(self) -> str:
        return "\\n\\n".join(p.text for p in self.pages)

    def to_dict(self) -> dict:
        return {"path": self.path, "page_count": self.page_count,
                "pages": [p.to_dict() for p in self.pages[:10]],
                "metadata": self.metadata}


class PDFParser:
    """Extract text from PDF files."""

    def __init__(self, use_external: bool = False):
        self.use_external = use_external
        self.last_error: str | None = None

    def parse(self, path: str | Path) -> PDFDocument:
        """Parse a PDF and extract text per page."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")
        try:
            return self._parse_with_lib(path)
        except Exception as e:
            self.last_error = str(e)
            return self._parse_fallback(path)

    def _parse_with_lib(self, path: Path) -> PDFDocument:
        import PyPDF2
        doc = PDFDocument(path=str(path))
        try:
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                doc.page_count = len(reader.pages)
                for i, page in enumerate(reader.pages):
                    doc.pages.append(PDFPage(page_num=i, text=page.extract_text() or ""))
            return doc
        except Exception:
            raise

    def _parse_fallback(self, path: Path) -> PDFDocument:
        """Fallback: extract raw text from the PDF bytes."""
        data = path.read_bytes()
        text_chunks = []
        for chunk in data.split(b"/Page"):
            chunk = chunk.split(b"endobj", 1)[0].split(b"BT", 1)[0]
            text = chunk.decode("latin-1", errors="ignore")
            lines = [l for l in text.split("\\n") if l.strip() and len(l) > 5]
            text_chunks.append("\\n".join(lines))
        doc = PDFDocument(path=str(path), page_count=max(1, len(text_chunks)))
        for i, t in enumerate(text_chunks):
            doc.pages.append(PDFPage(page_num=i, text=t.strip()))
        return doc

    def parse_many(self, paths: list[str]) -> list[PDFDocument]:
        """Parse multiple PDFs."""
        return [self.parse(p) for p in paths]

    def extract_text(self, path: str | Path) -> str:
        """Extract all text from a PDF."""
        return self.parse(path).to_text()
'''
    write_module("43_pdf_parser", code)
    return "module: astrovox/phases/phase43_pdf_parser.py"


def build_phase_43_docx_parser() -> str:
    """DOCX (Word) document parser."""
    code = '''"""DOCX (Microsoft Word) document parser."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator


@dataclass
class DOCXParagraph:
    """A paragraph in a DOCX document."""
    text: str
    is_heading: bool = False
    level: int = 0

    def to_dict(self) -> dict:
        return {"text": self.text, "is_heading": self.is_heading, "level": self.level}


@dataclass
class DOCXDocument:
    """A parsed DOCX document."""
    path: str
    paragraphs: list[DOCXParagraph] = field(default_factory=list)
    title: str = ""
    metadata: dict = field(default_factory=dict)

    def to_text(self) -> str:
        lines = []
        for p in self.paragraphs:
            if p.is_heading:
                lines.append(f"{'#' * (p.level + 1)} {p.text}")
            else:
                lines.append(p.text)
        return "\\n\\n".join(lines)

    def to_dict(self) -> dict:
        return {"path": self.path, "title": self.title,
                "paragraphs": [p.to_dict() for p in self.paragraphs[:50]],
                "metadata": self.metadata}


class DOCXParser:
    """Parse DOCX files into structured text."""

    def __init__(self, use_external: bool = False):
        self.use_external = use_external
        self.last_error: str | None = None

    def parse(self, path: str | Path) -> DOCXDocument:
        """Parse a DOCX file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"DOCX not found: {path}")
        try:
            return self._parse_with_lib(path)
        except Exception as e:
            self.last_error = str(e)
            return self._parse_fallback(path)

    def _parse_with_lib(self, path: Path) -> DOCXDocument:
        import docx
        doc = docx.Document(str(path))
        parsed = DOCXDocument(path=str(path))
        for para in doc.paragraphs:
            style = para.style.name if para.style else ""
            parsed.paragraphs.append(DOCXParagraph(
                text=para.text,
                is_heading="Heading" in style,
                level=int(style.split()[-1]) if "Heading" in style else 0))
        parsed.title = doc.core_properties.title or ""
        parsed.metadata = {k: v for k, v in doc.core_properties.__dict__.items() if v}
        return parsed

    def _parse_fallback(self, path: Path) -> DOCXDocument:
        data = path.read_bytes()
        text = data.decode("utf-8", errors="ignore")
        paragraphs = [l for l in text.split("\\n") if l.strip()]
        parsed = DOCXDocument(path=str(path), paragraphs=[
            DOCXParagraph(text=p) for p in paragraphs])
        return parsed

    def parse_many(self, paths: list[str]) -> list[DOCXDocument]:
        """Parse multiple DOCX files."""
        return [self.parse(p) for p in paths]

    def extract_text(self, path: str | Path) -> str:
        """Extract all text from a DOCX."""
        return self.parse(path).to_text()
'''
    write_module("43_docx_parser", code)
    return "module: astrovox/phases/phase43_docx_parser.py"


def build_phase_43_markdown_parser() -> str:
    """Markdown document parser."""
    code = '''"""Markdown document parser producing structured content."""

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
                parts.append(f"```\\n{b.content}\\n```")
            else:
                parts.append(b.content)
        return "\\n\\n".join(parts)

    def to_dict(self) -> dict:
        return {"path": self.path, "title": self.title,
                "blocks": [b.to_dict() for b in self.blocks]}


class MarkdownParser:
    """Parse Markdown files into structured blocks."""

    HEADING_RE = re.compile(r"^(#{1,6})\\s+(.*)$")
    CODE_BLOCK_RE = re.compile(r"^```(?:\\w+)?\\n(.*)^```", re.S)
    LIST_RE = re.compile(r"^[-*+]\\s+(.*)$")
    QUOTE_RE = re.compile(r"^>\\s*(.*)$")

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
                doc.blocks.append(MDBlock(kind="code", content="\\n".join(code_lines)))
                i += 1
                continue
            if self.LIST_RE.match(line):
                items = []
                while i < len(lines) and self.LIST_RE.match(lines[i]):
                    items.append(self.LIST_RE.match(lines[i]).group(1))
                    i += 1
                doc.blocks.append(MDBlock(kind="list", content="\\n".join(items)))
                continue
            if self.QUOTE_RE.match(line):
                items = []
                while i < len(lines) and self.QUOTE_RE.match(lines[i]):
                    items.append(self.QUOTE_RE.match(lines[i]).group(1))
                    i += 1
                doc.blocks.append(MDBlock(kind="blockquote", content="\\n".join(items)))
                continue
            doc.blocks.append(MDBlock(kind="paragraph", content=line))
            i += 1
        return doc

    def parse_many(self, paths: list[str]) -> list[MarkdownDocument]:
        """Parse multiple Markdown files."""
        return [self.parse(p) for p in paths]
'''
    write_module("43_markdown_parser", code)
    return "module: astrovox/phases/phase43_markdown_parser.py"


def build_phase_43_chunking_engine() -> str:
    """Recursive text chunking with overlap."""
    code = '''"""Recursive semantic chunking with configurable size and overlap."""

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

    SEPARATORS = ["\\n\\n\\n", "\\n\\n", "\\n", ". ", " ! ", " ? ", " "]
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
            if len("\\n".join(combined)) >= self.chunk_size:
                joined = "\\n".join(combined[:-1])
                if len(joined) >= self.min_chunk:
                    chunks.append(Chunk(id=self._next_id(), text=joined))
                combined = [combined[-1]]
        if combined:
            joined = "\\n".join(combined)
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
'''
    write_module("43_chunking_engine", code)
    return "module: astrovox/phases/phase43_chunking_engine.py"


def build_phase_43_embedding_pipeline() -> str:
    """Chunk-to-embedding production pipeline."""
    code = '''"""Pipeline: load docs -> chunk -> embed -> store."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from astrovox.phases._shared.base import BaseStore
from astrovox.phases._shared.retrieval_engine import EmbeddingVector, simple_text_embedding


@dataclass
class EmbeddedChunk:
    """A chunk with its embedding and metadata."""
    id: str
    text: str
    embedding: list[float]
    metadata: dict = field(default_factory=dict)
    source: str = ""
    chunk_index: int = 0

    def to_dict(self) -> dict:
        return {"id": self.id, "text": self.text[:500], "embedding": self.embedding[:16],
                "metadata": self.metadata, "source": self.source, "chunk_index": self.chunk_index}


class EmbeddingPipeline:
    """Produce embeddings for document chunks."""

    def __init__(self, dim: int = 8, normalize: bool = True):
        self.dim = dim
        self.normalize = normalize
        self.embeddings: dict[str, EmbeddingVector] = {}
        self.chunks: list[EmbeddedChunk] = []

    def _embed(self, text: str) -> list[float]:
        vec = simple_text_embedding(text, dim=self.dim, normalize=self.normalize)
        self.embeddings[text] = vec
        return vec.to_list()

    def embed_chunk(self, chunk_text: str, source: str = "", metadata: dict | None = None,
                    chunk_index: int = 0) -> EmbeddedChunk:
        """Embed a single chunk."""
        emb = self._embed(chunk_text)
        chunk = EmbeddedChunk(id=f"chunk_{len(self.chunks)}", text=chunk_text,
                              embedding=emb, source=source, chunk_index=chunk_index,
                              metadata=metadata or {})
        self.chunks.append(chunk)
        return chunk

    def embed_many(self, items: list[tuple[str, str]], metadata: dict | None = None) -> list[EmbeddedChunk]:
        """Embed multiple (text, source) pairs."""
        out = []
        for i, (text, source) in enumerate(items):
            out.append(self.embed_chunk(text, source=source, metadata=metadata, chunk_index=i))
        return out

    def store(self, store: BaseStore, prefix: str = "emb") -> int:
        """Store embedded chunks in a persistent store."""
        count = 0
        for chunk in self.chunks:
            key = f"{prefix}:{chunk.id}"
            store.set(key, chunk.to_dict())
            count += 1
        return count

    def count(self) -> int:
        return len(self.chunks)

    def reset(self) -> None:
        self.chunks.clear()
        self.embeddings.clear()
'''
    write_module("43_embedding_pipeline", code)
    return "module: astrovox/phases/phase43_embedding_pipeline.py"


def build_phase_43_retriever() -> str:
    """Vector similarity retrieval."""
    code = '''"""Vector similarity retrieval over embedded chunks."""

from __future__ import annotations

from typing import Any

from astrovox.phases._shared.base import BaseStore
from astrovox.phases._shared.retrieval_engine import EmbeddingVector, simple_text_embedding
from astrovox.phases._shared.ranking import Ranker


class VectorRetriever:
    """Retrieve chunks by vector similarity."""

    def __init__(self, store: BaseStore, dim: int = 8, top_k: int = 10,
                 min_score: float = 0.0):
        self.store = store
        self.dim = dim
        self.top_k = top_k
        self.min_score = min_score
        self.ranker = Ranker()

    def search(self, query: str, filters: dict | None = None, top: int | None = None) -> list[dict]:
        """Retrieve most similar chunks for a query."""
        top = top or self.top_k
        qvec = simple_text_embedding(query, dim=self.dim)
        results = []
        for key in self.store.list_keys():
            if filters and not self._matches(key, filters):
                continue
            entry = self.store.get(key)
            if not isinstance(entry, dict):
                continue
            emb_key = f"{key}:embedding"
            emb_data = self.store.get(emb_key)
            if isinstance(emb_data, dict) and "embedding" in emb_data:
                emb = EmbeddingVector(emb_data["embedding"], dim=self.dim)
            else:
                emb = qvec
            score = qvec.similarity(emb)
            if score >= self.min_score:
                results.append({"key": key, "score": score, "text": entry.get("text", ""),
                                "metadata": entry.get("metadata", {})})
        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:top]

    def _matches(self, key: str, filters: dict) -> bool:
        for k, v in filters.items():
            if k not in key:
                return False
        return True

    def top_similar(self, text: str, top: int | None = None) -> list[dict]:
        """Find the most similar stored items to a text."""
        qvec = simple_text_embedding(text, dim=self.dim)
        scored = []
        for key in self.store.list_keys():
            if not key.endswith(":embedding"):
                continue
            emb_data = self.store.get(key)
            if isinstance(emb_data, dict):
                emb = EmbeddingVector(emb_data["embedding"], dim=self.dim)
                scored.append((qvec.similarity(emb), key))
        scored.sort(reverse=True)
        out = []
        for score, key in scored[:top or self.top_k]:
            k = key.replace(":embedding", "")
            entry = self.store.get(k)
            out.append({"key": k, "score": score,
                        "text": entry.get("text", "") if isinstance(entry, dict) else str(entry)})
        return out
'''
    write_module("43_retriever", code)
    return "module: astrovox/phases/phase43_retriever.py"


def build_phase_43_reranker() -> str:
    """Cross-encoder-style re-ranking of retrieved results."""
    code = '''"""Re-rank retrieved results using scoring heuristics."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RankedResult:
    """A ranked retrieval result."""
    item: dict
    relevance_score: float
    position: int

    def to_dict(self) -> dict:
        return {"item": self.item, "relevance_score": self.relevance_score,
                "position": self.position}


class SimpleReranker:
    """Re-rank results using hybrid scoring (no external model needed)."""

    def __init__(self, use_keyword: bool = True, use_overlap: bool = True,
                 use_position: bool = True):
        self.use_keyword = use_keyword
        self.use_overlap = use_overlap
        self.use_position = use_position

    def _keyword_overlap(self, query: str, text: str) -> float:
        q = query.lower().split()
        t = text.lower().split()
        if not q or not t:
            return 0.0
        common = set(q) & set(t)
        return len(common) / len(q)

    def _embed_overlap(self, query: str, text: str, dim: int = 8) -> float:
        from astrovox.phases._shared.retrieval_engine import EmbeddingVector, simple_text_embedding
        q = simple_text_embedding(query, dim=dim)
        t = simple_text_embedding(text, dim=dim)
        return q.similarity(t)

    def score_item(self, query: str, item: dict) -> float:
        """Score a single item against the query."""
        text = item.get("text", "")
        score = 0.0
        if self.use_keyword:
            score += 3.0 * self._keyword_overlap(query, text)
        if self.use_overlap:
            score += 2.0 * self._embed_overlap(query, text)
        if self.use_position and "position" in item:
            score += 1.0 / (1.0 + item["position"])
        return score

    def rerank(self, query: str, items: list[dict], top: int = 10) -> list[RankedResult]:
        """Re-rank a list of items by relevance to the query."""
        scored = []
        for i, item in enumerate(items):
            s = self.score_item(query, item)
            scored.append(RankedResult(item=item, relevance_score=s, position=i))
        scored.sort(key=lambda r: r.relevance_score, reverse=True)
        return scored[:top]

    def rerank_store(self, store, query: str, top: int = 10) -> list[RankedResult]:
        """Retrieve and rerank from a store."""
        keys = list(store.list_keys())[:50]
        items = []
        for i, k in enumerate(keys):
            entry = store.get(k)
            if isinstance(entry, dict):
                items.append({"key": k, "text": entry.get("text", ""), "position": i})
        return self.rerank(query, items, top=top)
'''
    write_module("43_reranker", code)
    return "module: astrovox/phases/phase43_reranker.py"


def build_phase_43_citation_engine() -> str:
    """Source attribution & citation generation."""
    code = '''"""Generate citations for retrieved sources."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Citation:
    """A citation linking generated text to a source."""
    ref_id: str
    source_key: str
    source_label: str
    snippet: str
    position: int = 0

    def to_dict(self) -> dict:
        return {"ref_id": self.ref_id, "source_key": self.source_key,
                "source_label": self.source_label, "snippet": self.snippet,
                "position": self.position}

    def format(self) -> str:
        return f"[{self.ref_id}] {self.source_label}: {self.snippet[:80]}"


class CitationEngine:
    """Generate citations for retrieved sources."""

    def __init__(self, start: int = 1):
        self.start = start
        self.refs: list[Citation] = []

    def cite(self, source_key: str, source_label: str, snippet: str,
             position: int = 0) -> Citation:
        """Create a citation for a source."""
        ref_id = f"[{self.start + len(self.refs)}]"
        cit = Citation(ref_id=ref_id, source_key=source_key, source_label=source_label,
                       snippet=snippet, position=position)
        self.refs.append(cit)
        return cit

    def cite_batch(self, sources: list[dict]) -> list[Citation]:
        """Create citations for multiple sources."""
        return [self.cite(s.get("key", ""), s.get("label", "source"),
                          s.get("snippet", s.get("text", "") or "")[:200]) for s in sources]

    def build_response(self, response: str) -> str:
        """Append citations to a response."""
        out = response
        if self.refs:
            out += "\\n\\n---\\nSources:\\n"
            out += "\\n".join(c.format() for c in self.refs)
        return out

    def clear(self) -> None:
        self.refs.clear()

    def list_citations(self) -> list[dict]:
        return [c.to_dict() for c in self.refs]
'''
    write_module("43_citation_engine", code)
    return "module: astrovox/phases/phase43_citation_engine.py"


# ============ PHASE 44 - Search Engine ============

def build_phase_44_local_search() -> str:
    """In-memory keyword search."""
    code = '''"""In-memory keyword search over stored text."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SearchHit:
    """A single search hit."""
    key: str
    score: float
    text: str
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"key": self.key, "score": self.score, "text": self.text,
                "metadata": self.metadata}


class LocalSearch:
    """Fast in-memory keyword search."""

    def __init__(self):
        self.index: dict[str, list[tuple[str, int]]] = {}
        self.documents: dict[str, dict] = {}

    def add(self, key: str, text: str, metadata: dict | None = None) -> None:
        """Index a document."""
        text = str(text)
        self.documents[key] = {"text": text, "metadata": metadata or {}}
        tokens = text.lower().split()
        for token in tokens:
            self.index.setdefault(token, []).append((key, len(self.index.get(token, []))))

    def search(self, query: str, top: int = 10) -> list[SearchHit]:
        """Search for the query terms."""
        q = query.lower().split()
        scores: dict[str, float] = {}
        for token in q:
            for key, _ in self.index.get(token, []):
                scores[key] = scores.get(key, 0.0) + 1.0
        hits = []
        for key, score in scores.items():
            doc = self.documents[key]
            hits.append(SearchHit(key=key, score=score, text=doc["text"],
                                  metadata=doc.get("metadata", {})))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:top]

    def count(self) -> int:
        return len(self.documents)

    def clear(self) -> None:
        self.index.clear()
        self.documents.clear()
'''
    write_module("44_local_search", code)
    return "module: astrovox/phases/phase44_local_search.py"


def build_phase_44_hybrid_search() -> str:
    """Keyword + vector search fusion."""
    code = '''"""Fuse keyword and vector search results."""

from __future__ import annotations

from typing import Any

from astrovox.phases._shared.retrieval_engine import EmbeddingVector, simple_text_embedding
from astrovox.phases._shared.ranking import hybrid_rank


class HybridSearch:
    """Fuse keyword and semantic search results."""

    def __init__(self, keyword_weight: float = 0.5, semantic_weight: float = 0.5,
                 dim: int = 8):
        self.keyword_weight = keyword_weight
        self.semantic_weight = semantic_weight
        self.dim = dim
        self._keywords: dict[str, dict] = {}
        self._embeddings: dict[str, EmbeddingVector] = {}
        self._docs: dict[str, dict] = {}

    def add(self, key: str, text: str, metadata: dict | None = None) -> None:
        """Add a document to the hybrid index."""
        text = str(text)
        self._keywords.setdefault(key, {"count": 0})
        for token in text.lower().split():
            self._keywords.setdefault(token, []).append(key)
            self._keywords[key]["count"] = self._keywords[key].get("count", 0) + 1
        self._embeddings[key] = simple_text_embedding(text, dim=self.dim)
        self._docs[key] = {"text": text, "metadata": metadata or {}}

    def search(self, query: str, top: int = 10) -> list[dict]:
        """Fuse keyword and semantic results."""
        q = query.lower()
        # Keyword scores.
        kw_scores: dict[str, float] = {}
        for token in q.split():
            for key in self._keywords.get(token, []):
                kw_scores[key] = kw_scores.get(key, 0.0) + 1.0
        # Semantic score.
        qvec = simple_text_embedding(query, dim=self.dim)
        sem_scores: dict[str, float] = {}
        for key, vec in self._embeddings.items():
            sem_scores[key] = qvec.similarity(vec)
        # Fuse.
        all_keys = set(kw_scores) | set(sem_scores)
        scored = []
        for key in all_keys:
            kw = kw_scores.get(key, 0.0) / max(self._keywords.get(key, {}).get("count", 1), 1)
            sem = sem_scores.get(key, 0.0)
            total = kw * self.keyword_weight + sem * self.semantic_weight
            scored.append((total, key))
        scored.sort(reverse=True)
        out = []
        for score, key in scored[:top]:
            doc = self._docs[key]
            out.append({"key": key, "score": score, "text": doc["text"],
                        "metadata": doc.get("metadata", {})})
        return out

    def count(self) -> int:
        return len(self._docs)

    def clear(self) -> None:
        self._keywords.clear()
        self._embeddings.clear()
        self._docs.clear()
'''
    write_module("44_hybrid_search", code)
    return "module: astrovox/phases/phase44_hybrid_search.py"


def build_phase_44_semantic_search() -> str:
    """Embedding-based semantic search."""
    code = '''"""Semantic search using text embeddings."""

from __future__ import annotations

from astrovox.phases._shared.retrieval_engine import EmbeddingVector, simple_text_embedding


class SemanticSearch:
    """Semantic search over indexed documents."""

    def __init__(self, dim: int = 8):
        self.dim = dim
        self._docs: list[dict] = []
        self._vecs: list[EmbeddingVector] = []

    def add(self, key: str, text: str, metadata: dict | None = None) -> None:
        """Add a document."""
        text = str(text)
        self._docs.append({"key": key, "text": text, "metadata": metadata or {}})
        self._vecs.append(simple_text_embedding(text, dim=self.dim))

    def search(self, query: str, top: int = 10) -> list[dict]:
        """Search semantically."""
        qvec = simple_text_embedding(query, dim=self.dim)
        scored = [(qvec.similarity(v), doc) for v, doc in zip(self._vecs, self._docs)]
        scored.sort(reverse=True)
        return [{"key": d["key"], "score": s, "text": d["text"], "metadata": d["metadata"]}
                for s, d in scored[:top]]

    def count(self) -> int:
        return len(self._docs)

    def clear(self) -> None:
        self._docs.clear()
        self._vecs.clear()
'''
    write_module("44_semantic_search", code)
    return "module: astrovox/phases/phase44_semantic_search.py"


def build_phase_44_keyword_search() -> str:
    """BM25/TF-IDF keyword scoring search."""
    code = '''"""Keyword search using TF-IDF / BM25-style scoring."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class KeywordHit:
    """A keyword search hit."""
    key: str
    score: float
    text: str

    def to_dict(self) -> dict:
        return {"key": self.key, "score": self.score, "text": self.text}


class KeywordSearch:
    """TF-IDF/BM25-style keyword search."""

    def __init__(self, k1: float = 1.5, b: float = 0.75, delta: float = 1.2):
        self.k1 = k1
        self.b = b
        self.delta = delta
        self._docs: list[dict] = []
        self._index: dict[str, dict[str, int]] = {}
        self._doc_lens: dict[str, int] = {}

    def _term_freq(self, term: str, text: str) -> float:
        return text.lower().count(term) / max(len(text.split()), 1)

    def _inverse_doc_freq(self, term: str) -> float:
        docs_with = sum(1 for t in self._index.values() if term in t)
        return math.log((len(self._docs) + 1) / (docs_with + 1)) + 1.0

    def add(self, key: str, text: str, metadata: dict | None = None) -> None:
        """Index a document."""
        text = str(text).lower()
        self._docs.append({"key": key, "text": text, "metadata": metadata or {}})
        self._doc_lens[key] = len(text.split())
        terms = {}
        for t in text.split():
            terms[t] = terms.get(t, 0) + 1
        self._index[key] = terms

    def search(self, query: str, top: int = 10) -> list[KeywordHit]:
        """Search using BM25-style scoring."""
        q_terms = query.lower().split()
        scores: dict[str, float] = {}
        avg_dl = sum(self._doc_lens.values()) / max(len(self._docs), 1)
        for term in q_terms:
            idf = self._inverse_doc_freq(term)
            for key, terms in self._index.items():
                if term not in terms:
                    continue
                tf = self._term_freq(term, self._docs[key]["text"])
                dl = self._doc_lens[key]
                bm25 = idf * tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * dl / max(avg_dl, 1)))
                scores[key] = scores.get(key, 0.0) + bm25
        hits = []
        for key, score in scores.items():
            hits.append(KeywordHit(key=key, score=score, text=self._docs[key]["text"]))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:top]

    def count(self) -> int:
        return len(self._docs)

    def clear(self) -> None:
        self._docs.clear()
        self._index.clear()
        self._doc_lens.clear()
'''
    write_module("44_keyword_search", code)
    return "module: astrovox/phases/phase44_keyword_search.py"


def build_phase_44_search_ranking() -> str:
    """Ranking with recency, metadata boosts."""
    code = '''"""Search result ranking with recency and metadata boosts."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RankedHit:
    """A ranked search hit."""
    key: str
    score: float
    text: str
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"key": self.key, "score": self.score, "text": self.text,
                "metadata": self.metadata}


class SearchRanker:
    """Apply boosting factors to search results."""

    def __init__(self, recency_weight: float = 0.3, meta_boost: dict | None = None,
                 min_score: float = 0.0):
        self.recency_weight = recency_weight
        self.meta_boost = meta_boost or {}
        self.min_score = min_score

    def score(self, hit: dict, query: str | None = None) -> float:
        """Compute final score for a hit."""
        score = hit.get("score", 0.0)
        meta = hit.get("metadata", {})
        # Recency boost.
        created = meta.get("created", time.time())
        recency = 1.0 / (1.0 + (time.time() - created))
        score += self.recency_weight * recency * 10.0
        # Metadata boosts.
        for field_name, boost_val in self.meta_boost.items():
            if field_name in meta and meta[field_name] == boost_val:
                score += 1.0
        return score

    def rank(self, hits: list[dict], query: str | None = None, top: int = 10) -> list[RankedHit]:
        """Rank hits with boosting applied."""
        scored = []
        for h in hits:
            s = self.score(h, query)
            if s >= self.min_score:
                scored.append(RankedHit(key=h.get("key", ""), score=s, text=h.get("text", ""),
                                        metadata=h.get("metadata", {})))
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top]

    def boost_field(self, field_name: str, value: Any, boost: float = 1.0) -> None:
        """Add a metadata boost rule."""
        self.meta_boost[field_name] = value
        self.meta_boost[f"{field_name}:boost"] = boost
'''
    write_module("44_search_ranking", code)
    return "module: astrovox/phases/phase44_search_ranking.py"


def build_phase_44_search_cache() -> str:
    """Query result caching."""
    code = '''"""Cache for search query results."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class CacheEntry:
    """A cached query result."""
    query: str
    results: list[dict]
    score: float
    cached_at: float = field(default_factory=time.time)
    ttl: float = 3600.0

    def is_expired(self) -> bool:
        return time.time() > self.cached_at + self.ttl


class SearchCache:
    """In-memory cache for search results."""

    def __init__(self, max_size: int = 1000, default_ttl: float = 3600.0):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: dict[str, CacheEntry] = {}

    def _key(self, query: str, **kwargs) -> str:
        extras = " ".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return f"{query}|{extras}".lower()

    def get(self, query: str, **kwargs) -> list[dict] | None:
        key = self._key(query, **kwargs)
        entry = self._cache.get(key)
        if entry is None or entry.is_expired():
            return None
        return entry.results

    def put(self, query: str, results: list[dict], **kwargs) -> None:
        key = self._key(query, **kwargs)
        if len(self._cache) >= self.max_size:
            oldest = min(self._cache.values(), key=lambda e: e.cached_at)
            del self._cache[self._key(oldest.query, **{k: v for k, v in kwargs.items()})]
        self._cache[key] = CacheEntry(query=query, results=results, score=1.0)

    def hit(self, query: str, **kwargs) -> bool:
        return self.get(query, **kwargs) is not None

    def clear(self) -> None:
        self._cache.clear()

    def stats(self) -> dict:
        hits = 0
        total = 0
        return {"size": len(self._cache), "max_size": self.max_size,
                "ttl_seconds": self.default_ttl}
'''
    write_module("44_search_cache", code)
    return "module: astrovox/phases/phase44_search_cache.py"
