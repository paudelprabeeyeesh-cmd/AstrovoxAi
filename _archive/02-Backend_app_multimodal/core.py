"""Multimodal AI platform for AstrovoxAI.

Provides a unified pipeline for understanding and generating text, images,
audio, documents, and video.  Includes a shared embedding engine and a
multimodal retrieval service.
"""

from __future__ import annotations

import base64
import hashlib
import io
import math
import os
import struct
import time
import uuid
import wave
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from ..logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Shared types
# ---------------------------------------------------------------------------


class Modality(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    CONVERSATION = "conversation"


@dataclass
class MediaAsset:
    """Normalized representation of an uploaded media artifact."""

    id: str
    modality: Modality
    mime_type: str
    size_bytes: int
    bytes: Optional[bytes] = None
    source_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "modality": self.modality.value,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


@dataclass
class MultimodalChunk:
    """A slice of media content with optional embedding."""

    id: str
    asset_id: str
    modality: Modality
    text: str = ""
    position: int = 0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    page: Optional[int] = None
    bbox: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "modality": self.modality.value,
            "text": self.text,
            "position": self.position,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "page": self.page,
            "bbox": self.bbox,
            "metadata": self.metadata,
        }


@dataclass
class RetrievalHit:
    chunk: MultimodalChunk
    score: float
    source: str  # 'memory' | 'knowledge' | 'conversation' | 'asset'

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk": self.chunk.to_dict(),
            "score": round(self.score, 4),
            "source": self.source,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_id(prefix: str = "mm") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    dot = 0.0
    na = 0.0
    nb = 0.0
    for i in range(n):
        ai = a[i]
        bi = b[i]
        dot += ai * bi
        na += ai * ai
        nb += bi * bi
    if na == 0 or nb == 0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def detect_mime(name: str) -> str:
    ext = Path(name).suffix.lower()
    return {
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".html": "text/html",
        ".json": "application/json",
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".csv": "text/csv",
        ".epub": "application/epub+zip",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".flac": "audio/flac",
        ".ogg": "audio/ogg",
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
        ".webm": "video/webm",
        ".mkv": "video/x-matroska",
    }.get(ext, "application/octet-stream")


def modality_from_mime(mime: str) -> Modality:
    if mime.startswith("image/"):
        return Modality.IMAGE
    if mime.startswith("audio/"):
        return Modality.AUDIO
    if mime.startswith("video/"):
        return Modality.VIDEO
    if mime in {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/csv",
        "application/epub+zip",
        "text/markdown",
        "text/html",
    }:
        return Modality.DOCUMENT
    return Modality.TEXT


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------


class AssetStore:
    """In-memory store with optional disk persistence."""

    def __init__(self, base_dir: Optional[str] = None) -> None:
        self.base_dir = Path(
            base_dir or os.getenv("ASTROVOX_MM_DIR", "./storage/multimodal")
        )
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._assets: Dict[str, MediaAsset] = {}
        self._chunks: Dict[str, List[MultimodalChunk]] = defaultdict(list)
        self._embeddings: Dict[str, List[float]] = {}

    def add(self, asset: MediaAsset, chunks: Optional[List[MultimodalChunk]] = None) -> MediaAsset:
        self._assets[asset.id] = asset
        if chunks:
            self._chunks[asset.id] = chunks
        return asset

    def get(self, asset_id: str) -> Optional[MediaAsset]:
        return self._assets.get(asset_id)

    def chunks_for(self, asset_id: str) -> List[MultimodalChunk]:
        return list(self._chunks.get(asset_id, []))

    def add_chunks(self, asset_id: str, chunks: Iterable[MultimodalChunk]) -> None:
        for chunk in chunks:
            self._chunks[asset_id].append(chunk)
            if chunk.embedding is not None:
                self._embeddings[chunk.id] = chunk.embedding

    def store_embedding(self, chunk_id: str, embedding: List[float]) -> None:
        self._embeddings[chunk_id] = embedding

    def get_embedding(self, chunk_id: str) -> Optional[List[float]]:
        return self._embeddings.get(chunk_id)

    def all_chunks(self) -> List[MultimodalChunk]:
        out: List[MultimodalChunk] = []
        for chunks in self._chunks.values():
            out.extend(chunks)
        return out

    def list(self, modality: Optional[Modality] = None) -> List[MediaAsset]:
        items = list(self._assets.values())
        if modality is not None:
            items = [a for a in items if a.modality == modality]
        return items

    def remove(self, asset_id: str) -> None:
        self._assets.pop(asset_id, None)
        for chunk in self._chunks.pop(asset_id, []):
            self._embeddings.pop(chunk.id, None)

    def stats(self) -> Dict[str, Any]:
        per_modality: Dict[str, int] = defaultdict(int)
        for asset in self._assets.values():
            per_modality[asset.modality.value] += 1
        return {
            "assets": len(self._assets),
            "chunks": sum(len(v) for v in self._chunks.values()),
            "embeddings": len(self._embeddings),
            "by_modality": dict(per_modality),
        }