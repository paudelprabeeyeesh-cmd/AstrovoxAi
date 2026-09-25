"""Infinite Scroll with Infinite Data - Never-ending data streams."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DataChunk:
    chunk_id: str
    data: List[Any]
    cursor: str
    has_more: bool = True
    timestamp: float = field(default_factory=time.time)


class InfiniteScrollWithInfiniteData:
    """Provides infinite data streams for infinite scroll interfaces."""

    def __init__(self):
        self._streams: Dict[str, List[Any]] = {}
        self._cursors: Dict[str, str] = {}
        self._chunk_size: int = 50

    def register_stream(self, stream_id: str, initial_data: List[Any] = None) -> str:
        self._streams[stream_id] = initial_data or []
        self._cursors[stream_id] = "0"
        return stream_id

    def get_chunk(self, stream_id: str, cursor: str = None, limit: int = None) -> Optional[DataChunk]:
        if stream_id not in self._streams:
            return None
        data = self._streams[stream_id]
        cursor_int = int(cursor or self._cursors.get(stream_id, "0"))
        limit = limit or self._chunk_size
        end = cursor_int + limit
        chunk_data = data[cursor_int:end]
        has_more = end < len(data)
        if not has_more and len(data) > 0:
            new_data = [f"infinite_item_{uuid.uuid4().hex[:8]}" for _ in range(limit)]
            self._streams[stream_id].extend(new_data)
            chunk_data.extend(new_data[:limit])
            has_more = True
            end = cursor_int + limit
            has_more = end < len(self._streams[stream_id])
        chunk = DataChunk(
            chunk_id=str(uuid.uuid4()),
            data=chunk_data,
            cursor=str(end),
            has_more=has_more,
        )
        self._cursors[stream_id] = str(end)
        return chunk

    def append_data(self, stream_id: str, items: List[Any]) -> bool:
        if stream_id not in self._streams:
            return False
        self._streams[stream_id].extend(items)
        return True

    def get_stream_stats(self, stream_id: str) -> Dict[str, Any]:
        if stream_id not in self._streams:
            return {}
        return {
            "total_items": len(self._streams[stream_id]),
            "current_cursor": self._cursors.get(stream_id, "0"),
            "chunk_size": self._chunk_size,
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "streams": len(self._streams),
            "total_items": sum(len(v) for v in self._streams.values()),
        }
