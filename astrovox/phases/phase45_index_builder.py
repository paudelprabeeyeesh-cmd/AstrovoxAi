"""Construct and manage vector search indices."""

from __future__ import annotations

from astrovox.phases.phase45_embedding_storage import VectorStorage
from astrovox.phases.phase45_similarity_search import SimSearch, NaiveHNSW


class IndexBuilder:
    """Build vector search indices from stored vectors."""

    def __init__(self, storage: VectorStorage):
        self.storage = storage
        self.indices: dict[str, SimSearch | NaiveHNSW] = {}

    def build_brute(self, name: str = "brute", top: int = 10,
                    threshold: float = 0.0) -> SimSearch:
        """Build a brute-force similarity index."""
        vectors = {vid: rec.vector for vid, rec in self.storage._vectors.items()}
        idx = SimSearch(vectors=vectors)
        self.indices[name] = idx
        return idx

    def build_hnsw(self, name: str = "hnsw", m: int = 4) -> NaiveHNSW:
        """Build a naive HNSW index."""
        vectors = {vid: rec.vector for vid, rec in self.storage._vectors.items()}
        idx = NaiveHNSW(vectors=vectors, m=m)
        self.indices[name] = idx
        return idx

    def rebuild_all(self) -> dict[str, SimSearch | NaiveHNSW]:
        """Rebuild all index types."""
        return {"brute": self.build_brute(), "hnsw": self.build_hnsw()}

    def add_to_index(self, name: str, vid: str, vector: list[float]) -> None:
        """Add a vector to an existing index."""
        idx = self.indices.get(name)
        if isinstance(idx, (SimSearch, NaiveHNSW)):
            idx.add(vid, vector)

    def search(self, name: str, query: list[float], top: int = 10,
               threshold: float = 0.0) -> list[tuple[str, float]]:
        """Search using a named index."""
        idx = self.indices.get(name)
        if idx is None:
            raise KeyError(f"No index named {name}")
        return idx.search(query, top=top, threshold=threshold)

    def list_indices(self) -> list[str]:
        return list(self.indices.keys())

    def clear(self) -> None:
        self.indices.clear()
