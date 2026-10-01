"""Serialization for tensors and whole modules.

The on-disk format is a small self-describing container: a JSON header with
dtype, shape, and metadata, followed by raw little-endian element bytes. Using
raw bytes rather than ``pickle`` keeps checkpoints loadable without executing
arbitrary code, which matters for a platform that loads third-party weights.
"""

from __future__ import annotations

import io
import json
import struct
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

import numpy as np

from astrovox.tensor.dtype import BY_NAME, DType, from_numpy, resolve
from astrovox.tensor.shape import Shape
from astrovox.tensor.tensor import Tensor

#: Bumped when the container layout changes incompatibly.
FORMAT_VERSION = 1
_MAGIC = b"AVX1"


@dataclass
class TensorHeader:
    """Metadata describing one serialized tensor."""

    dtype: str
    shape: list[int]
    nbytes: int
    requires_grad: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return the header as a JSON-serializable dictionary."""
        return {
            "dtype": self.dtype,
            "shape": self.shape,
            "nbytes": self.nbytes,
            "requires_grad": self.requires_grad,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TensorHeader:
        """Rebuild a header from its dictionary form."""
        return cls(
            dtype=data["dtype"],
            shape=list(data["shape"]),
            nbytes=int(data["nbytes"]),
            requires_grad=bool(data.get("requires_grad", False)),
            metadata=dict(data.get("metadata", {})),
        )


def serialize_tensor(t: Tensor, metadata: dict[str, Any] | None = None) -> bytes:
    """Serialize one tensor to the container format."""
    dense = np.ascontiguousarray(t.numpy(), dtype=_little_endian(t.dtype).np_dtype)
    header = TensorHeader(
        dtype=t.dtype.name,
        shape=list(t.shape.dims),
        nbytes=int(dense.nbytes),
        requires_grad=t.requires_grad,
        metadata=metadata or {},
    )
    header_bytes = json.dumps(header.to_dict(), sort_keys=True).encode("utf-8")
    payload = dense.tobytes(order="C")

    out = io.BytesIO()
    out.write(_MAGIC)
    out.write(struct.pack("<I", FORMAT_VERSION))
    out.write(struct.pack("<I", len(header_bytes)))
    out.write(header_bytes)
    out.write(payload)
    return out.getvalue()


def deserialize_tensor(blob: bytes) -> Tensor:
    """Rebuild a tensor from the container format."""
    if blob[:4] != _MAGIC:
        raise ValueError("Not an Astrovox tensor blob: bad magic")
    version, header_len = struct.unpack("<II", blob[4:12])
    if version != FORMAT_VERSION:
        raise ValueError(f"Unsupported tensor format version {version}, expected {FORMAT_VERSION}")

    header = TensorHeader.from_dict(json.loads(blob[12 : 12 + header_len].decode("utf-8")))
    payload = blob[12 + header_len :]
    if len(payload) != header.nbytes:
        raise ValueError(f"Truncated tensor payload: expected {header.nbytes} bytes, got {len(payload)}")

    dtype = BY_NAME.get(header.dtype) or from_numpy(np.dtype(header.dtype))
    array = np.frombuffer(payload, dtype=_little_endian(dtype).np_dtype).copy()
    return Tensor.from_numpy(array.reshape(Shape(header.shape)), dtype)


def save_tensors(path: str | Path, tensors: dict[str, Tensor]) -> Path:
    """Write a named collection of tensors into a single zip archive."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {}
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, t in tensors.items():
            archive.writestr(f"tensors/{name}.avx", serialize_tensor(t))
            manifest[name] = {"dtype": t.dtype.name, "shape": list(t.shape.dims)}
        archive.writestr("manifest.json", json.dumps(manifest, indent=2, sort_keys=True))
    return target


def load_tensors(path: str | Path) -> dict[str, Tensor]:
    """Read a tensor archive written by :func:`save_tensors`."""
    with zipfile.ZipFile(Path(path), "r") as archive:
        return {
            name[len("tensors/") : -len(".avx")]: deserialize_tensor(archive.read(name))
            for name in archive.namelist()
            if name.startswith("tensors/") and name.endswith(".avx")
        }


def save_checkpoint(module: Any, path: str | Path, extra: dict[str, Any] | None = None) -> Path:
    """Serialize every parameter and buffer of ``module`` into a checkpoint.

    Args:
        module: an object exposing ``state_dict()`` and ``load_state_dict()``.
        path: destination file.
        extra: arbitrary JSON-serializable data to store alongside, such as
            optimizer state or the step counter.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    state = module.state_dict()
    manifest: dict[str, Any] = {"extra": extra or {}, "tensors": {}}
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, t in state.items():
            archive.writestr(f"tensors/{name}.avx", serialize_tensor(t))
            manifest["tensors"][name] = {"dtype": t.dtype.name, "shape": list(t.shape.dims)}
        archive.writestr("manifest.json", json.dumps(manifest, indent=2, sort_keys=True))
    return target


def load_checkpoint(module: Any, path: str | Path, strict: bool = True) -> dict[str, Any]:
    """Load a checkpoint written by :func:`save_checkpoint`` into ``module``.

    Returns the extra metadata recorded alongside the tensors.
    """
    with zipfile.ZipFile(Path(path), "r") as archive:
        state: dict[str, Tensor] = {}
        for name in archive.namelist():
            if name.startswith("tensors/") and name.endswith(".avx"):
                state[name[len("tensors/") : -len(".avx")]] = deserialize_tensor(archive.read(name))
        manifest = json.loads(archive.read("manifest.json"))
    module.load_state_dict(state, strict=strict)
    return manifest.get("extra", {})


def iter_tensors(path: str | Path) -> Iterator[tuple[str, Tensor]]:
    """Yield ``(name, tensor)`` pairs from an archive without loading all of it."""
    with zipfile.ZipFile(Path(path), "r") as archive:
        for name in archive.namelist():
            if name.startswith("tensors/") and name.endswith(".avx"):
                yield name[len("tensors/") : -len(".avx")], deserialize_tensor(archive.read(name))


def _little_endian(dtype: DType) -> DType:
    """Return the little-endian variant of ``dtype`` for stable bytes on disk."""
    little = np.dtype(dtype.np_dtype).newbyteorder("<")
    if little.isnative:
        return dtype
    return from_numpy(little)


def dtype_size(dtype: DType | str) -> int:
    """Return the element width of ``dtype`` in bytes."""
    return resolve(dtype).bits // 8
