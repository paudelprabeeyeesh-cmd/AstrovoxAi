"""High-level Intermediate Representation (HIR).

HIR is a typed, immutable representation of the program after semantic analysis.
It preserves high-level structure while adding type information.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from ..executor.dsl import Statement


@dataclass(frozen=True)
class HIRType:
    """Type representation in HIR."""

    name: str
    generic_params: Tuple["HIRType", ...] = ()
    nullable: bool = False

    def __str__(self) -> str:
        params = f"[{', '.join(str(p) for p in self.generic_params)}]" if self.generic_params else ""
        nullable = "?" if self.nullable else ""
        return f"{self.name}{params}{nullable}"


@dataclass(frozen=True)
class HIRVariable:
    """Typed variable in HIR."""

    name: str
    type: HIRType
    mutable: bool = False
    source_location: Optional[Tuple[int, int]] = None


@dataclass(frozen=True)
class HIRBlock:
    """Basic block in HIR (sequence of statements)."""

    id: str
    statements: Tuple[Any, ...]  # HIR statements
    predecessors: Tuple[str, ...] = ()
    successors: Tuple[str, ...] = ()


@dataclass(frozen=True)
class HIRFunction:
    """Function definition in HIR."""

    name: str
    params: Tuple[HIRVariable, ...]
    return_type: HIRType
    body: Tuple[HIRBlock, ...]
    entry_block: str
    locals: Dict[str, HIRVariable] = field(default_factory=dict)
    signature_hash: str = ""

    def __post_init__(self) -> None:
        if not self.signature_hash:
            object.__setattr__(
                self,
                "signature_hash",
                hashlib.sha256(
                    f"{self.name}:{self.return_type}:{[str(p.type) for p in self.params]}".encode()
                ).hexdigest()[:16],
            )


@dataclass(frozen=True)
class HIRModule:
    """Top-level HIR module."""

    name: str
    functions: Dict[str, HIRFunction]
    types: Dict[str, HIRType]
    globals: Dict[str, HIRVariable]
    source_hash: str = ""
    compiled_at: float = field(default_factory=time.time)

    def get_function(self, name: str) -> Optional[HIRFunction]:
        """Get function by name."""
        return self.functions.get(name)

    def get_type(self, name: str) -> Optional[HIRType]:
        """Get type by name."""
        return self.types.get(name)


class HIRBuilder:
    """Builds HIR from AST."""

    def __init__(self) -> None:
        self._functions: Dict[str, HIRFunction] = {}
        self._types: Dict[str, HIRType] = {}
        self._globals: Dict[str, HIRVariable] = {}
        self._type_counter = 0

    def build_from_ast(self, ast: Any) -> HIRModule:
        """Build HIR from AST (placeholder)."""
        return HIRModule(
            name="module",
            functions=self._functions,
            types=self._types,
            globals=self._globals,
        )

    def infer_type(self, expr: Any) -> HIRType:
        """Infer type from expression."""
        return HIRType("any")
