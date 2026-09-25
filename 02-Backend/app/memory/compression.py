"""Memory compression for storage efficiency."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
import zlib
import base64


@dataclass
class CompressedMemory:
    memory_id: str
    compressed_content: bytes
    original_size: int
    compressed_size: int
    compression_ratio: float
    algorithm: str = "zlib"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MemoryCompressor:
    @staticmethod
    def compress(content: str, algorithm: str = "zlib") -> CompressedMemory:
        original_size = len(content.encode())
        if algorithm == "zlib":
            compressed = zlib.compress(content.encode())
        elif algorithm == "base64+zlib":
            compressed = base64.b64encode(zlib.compress(content.encode()))
        else:
            compressed = content.encode()
        compressed_size = len(compressed)
        ratio = compressed_size / original_size if original_size > 0 else 0.0
        memory_id = f"comp_{datetime.now(timezone.utc).timestamp()}"
        return CompressedMemory(
            memory_id=memory_id,
            compressed_content=compressed,
            original_size=original_size,
            compressed_size=compressed_size,
            compression_ratio=ratio,
            algorithm=algorithm,
        )

    @staticmethod
    def decompress(compressed_memory: CompressedMemory) -> str:
        if compressed_memory.algorithm == "zlib":
            return zlib.decompress(compressed_memory.compressed_content).decode()
        elif compressed_memory.algorithm == "base64+zlib":
            return zlib.decompress(base64.b64decode(compressed_memory.compressed_content)).decode()
        return compressed_memory.compressed_content.decode()
