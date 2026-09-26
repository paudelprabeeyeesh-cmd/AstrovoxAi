"""Vector index management with namespace isolation."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .database import VectorDatabase, VectorRecord

logger = logging.getLogger(__name__)


class VectorIndexManager:
    """Manage multiple named vector indexes (namespaces)."""

    def __init__(self, default_dim: int = 1536):
        self.default_dim = default_dim
        self._indexes: Dict[str, VectorDatabase] = {}

    def _get_index(self, namespace: str) -> VectorDatabase:
        if namespace not in self._indexes:
            self._indexes[namespace] = VectorDatabase(dim=self.default_dim)
        return self._indexes[namespace]

    def upsert(self, namespace: str, records: List[VectorRecord]) -> None:
        index = self._get_index(namespace)
        index.upsert(records)

    def search(self, namespace: str, query_vector: List[float], top_k: int = 10,
               filter_metadata: Optional[Dict[str, Any]] = None,
               threshold: float = 0.0) -> List[Any]:
        index = self._get_index(namespace)
        return index.search(query_vector, top_k=top_k, filter_metadata=filter_metadata, threshold=threshold)

    def delete(self, namespace: str, id: str) -> bool:
        index = self._indexes.get(namespace)
        if not index:
            return False
        index.delete(id)
        return True

    def clear_namespace(self, namespace: str) -> None:
        if namespace in self._indexes:
            del self._indexes[namespace]

    def get_stats(self, namespace: str) -> Dict[str, Any]:
        index = self._indexes.get(namespace)
        if not index:
            return {"namespace": namespace, "count": 0}
        return {"namespace": namespace, **index.get_stats()}

    def list_namespaces(self) -> List[str]:
        return list(self._indexes.keys())
