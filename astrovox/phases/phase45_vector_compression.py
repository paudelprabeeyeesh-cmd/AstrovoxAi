"""Vector compression via quantization and packing."""

from __future__ import annotations

import struct
from dataclasses import dataclass, field


@dataclass
class CompressedVector:
    """A compressed vector representation."""
    original: list[float]
    quantized: list[int]
    scale: float
    dtype_bits: int = 8

    def to_bytes(self) -> bytes:
        n = len(self.quantized)
        data = struct.pack(f"<{n}B", *self.quantized)
        return struct.pack("<f", self.scale) + data

    @classmethod
    def from_bytes(cls, data: bytes) -> "CompressedVector":
        scale = struct.unpack("<f", data[:4])[0]
        q = list(data[4:])
        return cls(quantized=q, scale=scale, dtype_bits=8)


class VectorCompressor:
    """Compress vectors via quantization and packing."""

    def __init__(self, bits: int = 8, min_val: float | None = None,
                 max_val: float | None = None):
        self.bits = bits
        self.min_val = min_val
        self.max_val = max_val
        self._tables: dict[str, CompressedVector] = {}

    def _quantize(self, val: float, min_v: float, max_v: float) -> int:
        range_v = max_v - min_v
        if range_v == 0:
            return 0
        scale = (2 ** self.bits) - 1
        return int((val - min_v) / range_v * scale)

    def compress(self, vector: list[float], key: str = "default") -> CompressedVector:
        """Compress a vector."""
        min_v = self.min_val if self.min_val is not None else min(vector)
        max_v = self.max_val if self.max_val is not None else max(vector)
        quantized = [self._quantize(v, min_v, max_v) for v in vector]
        cv = CompressedVector(original=vector, quantized=quantized,
                              scale=(max_v - min_v) / ((2 ** self.bits) - 1))
        self._tables[key] = cv
        return cv

    def decompress(self, key: str = "default") -> list[float]:
        """Decompress a stored vector."""
        cv = self._tables.get(key)
        if cv is None:
            raise KeyError(f"No compressed vector for key {key}")
        min_v = cv.scale * 0.0
        max_v = cv.scale * ((2 ** self.bits) - 1)
        return [self._quantize(q, 0, (2 ** self.bits) - 1) * cv.scale + min_v
                for q in cv.quantized]

    def compress_batch(self, vectors: list[list[float]], prefix: str = "v") -> dict[str, CompressedVector]:
        """Compress multiple vectors."""
        out = {}
        for i, v in enumerate(vectors):
            out[f"{prefix}_{i}"] = self.compress(v, key=f"{prefix}_{i}")
        return out

    def to_bytes_all(self) -> bytes:
        """Serialize all compressed vectors."""
        parts = []
        for key, cv in self._tables.items():
            parts.append(struct.pack("<I", len(key)) + key.encode("utf-8") + cv.to_bytes())
        return b"".join(parts)

    @classmethod
    def from_bytes(cls, data: bytes) -> "VectorCompressor":
        inst = cls()
        pos = 0
        while pos < len(data):
            klen = struct.unpack("<I", data[pos:pos + 4])[0]
            pos += 4
            key = data[pos:pos + klen].decode("utf-8")
            pos += klen
            cv = CompressedVector.from_bytes(data[pos:pos + 4 + 256])
            inst._tables[key] = cv
            pos += 4 + len(cv.quantized)
        return inst
