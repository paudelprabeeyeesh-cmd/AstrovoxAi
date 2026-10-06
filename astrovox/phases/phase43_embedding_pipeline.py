"""Pipeline: load docs -> chunk -> embed -> store."""

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
