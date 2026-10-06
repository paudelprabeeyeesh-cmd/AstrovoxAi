"""Filterable metadata storage for vectors."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetadataIndex:
    """An inverted index on a metadata field."""
    field_name: str
    values: dict[str, list[str]] = field(default_factory=dict)

    def add(self, vid: str, value: str) -> None:
        self.values.setdefault(value, []).append(vid)

    def remove(self, vid: str, value: str) -> None:
        vals = self.values.get(value, [])
        if vid in vals:
            vals.remove(vid)

    def lookup(self, value: str) -> list[str]:
        return self.values.get(value, [])


class MetadataStore:
    """Filterable metadata store."""

    def __init__(self):
        self._meta: dict[str, dict[str, Any]] = {}
        self._indexes: dict[str, MetadataIndex] = {}

    def set(self, vid: str, key: str, value: Any) -> None:
        self._meta.setdefault(vid, {})
        self._meta[vid][key] = value
        if isinstance(value, (str, int, float, bool)):
            self._index(vid, key, str(value))

    def _index(self, vid: str, key: str, value: str) -> None:
        idx = self._indexes.setdefault(key, MetadataIndex(field_name=key))
        idx.add(vid, value)

    def get(self, vid: str, key: str) -> Any:
        return self._meta.get(vid, {}).get(key)

    def filter(self, field: str, value: Any) -> list[str]:
        """Return vector IDs matching a metadata filter."""
        idx = self._indexes.get(str(field))
        if idx is None:
            return []
        return idx.lookup(str(value))

    def filters(self, **conditions) -> list[str]:
        """Return vector IDs matching all conditions."""
        if not conditions:
            return list(self._meta.keys())
        result: set[str] | None = None
        for field, value in conditions.items():
            idx = self._indexes.get(str(field))
            if idx is None:
                return []
            match = set(idx.lookup(str(value)))
            result = match if result is None else (result & match)
        return list(result or set())

    def list_ids(self) -> list[str]:
        return list(self._meta.keys())

    def count(self) -> int:
        return len(self._meta)

    def clear(self) -> None:
        self._meta.clear()
        self._indexes.clear()
