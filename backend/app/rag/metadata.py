"""Metadata extraction and filtering for RAG pipelines."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ChunkMetadata:
    document_id: str
    chunk_id: str
    filename: str = ""
    source_type: str = ""
    page: Optional[int] = None
    section: str = ""
    language: str = "en"
    created_at: str = ""
    author: str = ""
    tags: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)


class MetadataExtractor:
    def extract(self, document_id: str, chunk_id: str, content: str, source_type: str = "", filename: str = "") -> ChunkMetadata:
        return ChunkMetadata(
            document_id=document_id,
            chunk_id=chunk_id,
            filename=filename or document_id,
            source_type=source_type or "text",
            page=self._detect_page(content),
            section=self._detect_section(content),
            language=self._detect_language(content),
            author=self._detect_author(content),
            tags=self._detect_tags(content),
        )

    def _detect_page(self, content: str) -> Optional[int]:
        matches = re.findall(r"page\s+(\d+)", content, flags=re.IGNORECASE)
        if matches:
            try:
                return int(matches[0])
            except ValueError:
                pass
        return None

    def _detect_section(self, content: str) -> str:
        match = re.search(r"^(#{1,6})\s+(.+)", content, flags=re.MULTILINE)
        if match:
            return match.group(2).strip()
        return ""

    def _detect_language(self, content: str) -> str:
        if re.search(r"[\u4e00-\u9fff]", content):
            return "zh"
        if re.search(r"[\u0600-\u06ff]", content):
            return "ar"
        return "en"

    def _detect_author(self, content: str) -> str:
        match = re.search(r"by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", content)
        return match.group(1) if match else ""

    def _detect_tags(self, content: str) -> List[str]:
        tags = re.findall(r"#(\w+)", content)
        return list(dict.fromkeys(tags))


class MetadataFilter:
    def __init__(self, filters: Optional[Dict[str, Any]] = None):
        self.filters = filters or {}

    def apply(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not self.filters:
            return records
        filtered: List[Dict[str, Any]] = []
        for record in records:
            metadata = record.get("metadata", {})
            if self._matches(metadata):
                filtered.append(record)
        return filtered

    def _matches(self, metadata: Dict[str, Any]) -> bool:
        for key, value in self.filters.items():
            if key not in metadata:
                return False
            if isinstance(value, list):
                if metadata[key] not in value:
                    return False
            else:
                if metadata[key] != value:
                    return False
        return True
