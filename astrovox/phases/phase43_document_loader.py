"""Unified document loader for multiple file formats."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator


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
