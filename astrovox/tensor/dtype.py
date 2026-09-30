"""Scalar element types for the Astrovox tensor engine.

The engine stores every value in a NumPy buffer, but dtypes are first-class
objects here so that ``Tensor`` signatures stay explicit and the compiler can
reason about precision without inspecting raw buffers.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class DType:
    """A scalar element type.

    Attributes:
        name: canonical short name, e.g. ``"float32"``.
        np_dtype: the NumPy dtype backing every buffer of this type.
        is_float: whether the type supports fractional values.
        is_integer: whether the type is a signed or unsigned integer.
        is_complex: whether the type has a real and imaginary component.
        bits: storage width in bits.
    """

    name: str
    np_dtype: np.dtype
    is_float: bool
    is_integer: bool
    is_complex: bool = False
    bits: int = 32

    @property
    def is_floating(self) -> bool:
        """True for float and complex types, which carry gradients."""
        return self.is_float or self.is_complex

    def promote(self, other: DType) -> DType:
        """Return the type that holds both ``self`` and ``other`` without loss.

        Promotion follows NumPy's rules: integers promote to floats, low
        precision promotes to high precision, and complex absorbs real.
        """
        if other is self or other.name == self.name:
            return self
        if self.is_complex and not other.is_complex:
            return self
        if other.is_complex and not self.is_complex:
            return other
        if self.is_float and other.is_integer:
            return self if self.bits >= 32 else from_numpy(np.promote_types(self.np_dtype, np.float32))
        if other.is_float and self.is_integer:
            return other if other.bits >= 32 else from_numpy(np.promote_types(np.float32, other.np_dtype))
        if self.is_integer and other.is_integer:
            return from_numpy(np.promote_types(self.np_dtype, other.np_dtype))
        if self.is_float and other.is_float:
            return from_numpy(np.promote_types(self.np_dtype, other.np_dtype))
        return self

    def __str__(self) -> str:
        return self.name


def from_numpy(np_dtype: np.dtype) -> DType:
    """Build a :class:`DType` from a NumPy dtype."""
    resolved = np.dtype(np_dtype)
    kind = resolved.kind
    return DType(
        name=resolved.name,
        np_dtype=resolved,
        is_float=kind == "f",
        is_integer=kind in "iu",
        is_complex=kind == "c",
        bits=resolved.itemsize * 8,
    )


FLOAT16 = DType("float16", np.dtype(np.float16), True, False, bits=16)
BFLOAT16 = DType("bfloat16", np.dtype(np.float16), True, False, bits=16)
FLOAT32 = DType("float32", np.dtype(np.float32), True, False, bits=32)
FLOAT64 = DType("float64", np.dtype(np.float64), True, False, bits=64)
INT8 = DType("int8", np.dtype(np.int8), False, True, bits=8)
INT16 = DType("int16", np.dtype(np.int16), False, True, bits=16)
INT32 = DType("int32", np.dtype(np.int32), False, True, bits=32)
INT64 = DType("int64", np.dtype(np.int64), False, True, bits=64)
UINT8 = DType("uint8", np.dtype(np.uint8), False, True, bits=8)
BOOL = DType("bool", np.dtype(np.bool_), False, False, bits=8)

#: Mapping from canonical dtype name to :class:`DType`, used by deserialization.
BY_NAME: dict[str, DType] = {
    d.name: d
    for d in (
        FLOAT16,
        BFLOAT16,
        FLOAT32,
        FLOAT64,
        INT8,
        INT16,
        INT32,
        INT64,
        UINT8,
        BOOL,
    )
}

#: Default dtype for tensors created from Python floats.
DEFAULT = FLOAT32

#: Default dtype for tensors created from Python ints.
DEFAULT_INT = INT64

#: Accumulator dtype for reductions over a given input type.
_ACCUMULATOR = {
    "bool": INT64,
    "int8": INT64,
    "int16": INT64,
    "int32": INT64,
    "int64": INT64,
    "uint8": INT64,
    "float16": FLOAT32,
    "bfloat16": FLOAT32,
    "float32": FLOAT32,
    "float64": FLOAT64,
    "complex64": FLOAT64,
    "complex128": FLOAT64,
}


def accumulator_dtype(dtype: DType) -> DType:
    """Return the dtype NumPy accumulates reductions in for ``dtype``."""
    return _ACCUMULATOR.get(dtype.name, FLOAT32)


def resolve(value: DType | str | np.dtype | None, default: DType = DEFAULT) -> DType:
    """Coerce ``value`` into a :class:`DType`, falling back to ``default``."""
    if value is None:
        return default
    if isinstance(value, DType):
        return value
    if isinstance(value, str):
        try:
            return BY_NAME[value]
        except KeyError as exc:
            raise KeyError(f"Unknown dtype {value!r}. Known: {sorted(BY_NAME)}") from exc
    return from_numpy(value)
