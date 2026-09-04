"""Symbol database for incremental compilation.

Provides:
- Symbol table with scoping
- Type information
- Cross-reference tracking
- Dependency tracking for incremental compilation
- Source location mapping
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class SymbolKind(str, Enum):
    FUNCTION = "function"
    VARIABLE = "variable"
    TYPE = "type"
    MODULE = "module"
    PARAMETER = "parameter"
    STEP = "step"
    AGENT = "agent"
    TOOL = "tool"


@dataclass(frozen=True)
class SourceLocation:
    """Source code location."""

    file: str
    line: int
    column: int
    end_line: int = 0
    end_column: int = 0

    def __lt__(self, other: "SourceLocation") -> bool:
        if not isinstance(other, SourceLocation):
            return NotImplemented
        return (self.file, self.line, self.column) < (other.file, other.line, other.column)


@dataclass
class Symbol:
    """Symbol table entry."""

    name: str
    kind: SymbolKind
    type: Optional[str] = None
    location: Optional[SourceLocation] = None
    scope: str = "global"
    dependencies: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    hash: Optional[str] = None

    def compute_hash(self) -> str:
        """Compute content hash for change detection."""
        return hashlib.sha256(
            f"{self.name}:{self.kind}:{self.type}:{self.scope}".encode()
        ).hexdigest()[:16]


@dataclass
class Scope:
    """Variable/function scope."""

    name: str
    parent: Optional["Scope"]
    symbols: Dict[str, Symbol] = field(default_factory=dict)

    def define(self, symbol: Symbol) -> None:
        """Add symbol to scope."""
        self.symbols[symbol.name] = symbol

    def resolve(self, name: str) -> Optional[Symbol]:
        """Resolve symbol in this scope or parent scopes."""
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.resolve(name)
        return None


class SymbolDatabase:
    """Symbol database for incremental compilation.

    Tracks:
    - All symbols in the codebase
    - Dependency graph between symbols
    - Change tracking for incremental recompilation
    """

    def __init__(self) -> None:
        self._symbols: Dict[str, Symbol] = {}
        self._scopes: Dict[str, Scope] = {"global": Scope(name="global", parent=None)}
        self._dependencies: Dict[str, Set[str]] = {}
        self._file_hashes: Dict[str, str] = {}
        self._current_scope: str = "global"

    def enter_scope(self, name: str) -> None:
        """Enter a new scope."""
        parent = self._scopes[self._current_scope]
        self._scopes[name] = Scope(name=name, parent=parent)
        self._current_scope = name

    def exit_scope(self) -> None:
        """Exit current scope."""
        if self._current_scope != "global":
            scope = self._scopes[self._current_scope]
            self._current_scope = scope.parent.name if scope.parent else "global"

    def define(self, symbol: Symbol) -> None:
        """Define a symbol in current scope."""
        symbol.hash = symbol.compute_hash()
        self._symbols[symbol.name] = symbol
        self._scopes[self._current_scope].define(symbol)

    def resolve(self, name: str) -> Optional[Symbol]:
        """Resolve symbol by name."""
        return self._scopes[self._current_scope].resolve(name)

    def add_dependency(self, from_symbol: str, to_symbol: str) -> None:
        """Record dependency between symbols."""
        if from_symbol not in self._dependencies:
            self._dependencies[from_symbol] = set()
        self._dependencies[from_symbol].add(to_symbol)

    def get_dependents(self, symbol_name: str) -> Set[str]:
        """Get symbols that depend on given symbol."""
        return {s for s, deps in self._dependencies.items() if symbol_name in deps}

    def get_dependencies(self, symbol_name: str) -> Set[str]:
        """Get symbols that given symbol depends on."""
        return self._dependencies.get(symbol_name, set())

    def update_file_hash(self, filepath: str, content: str) -> bool:
        """Update file hash and detect changes."""
        new_hash = hashlib.sha256(content.encode()).hexdigest()
        old_hash = self._file_hashes.get(filepath)
        self._file_hashes[filepath] = new_hash
        return old_hash != new_hash

    def get_changed_symbols(self, filepath: str) -> List[Symbol]:
        """Get symbols that changed in a file."""
        # In production: compare old vs new AST
        return []

    def get_symbol(self, name: str) -> Optional[Symbol]:
        """Get symbol by name."""
        return self._symbols.get(name)

    def get_all_symbols(self) -> List[Symbol]:
        """Get all symbols."""
        return list(self._symbols.values())

    def stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        by_kind: Dict[str, int] = {}
        for sym in self._symbols.values():
            by_kind[sym.kind.value] = by_kind.get(sym.kind.value, 0) + 1
        return {
            "total_symbols": len(self._symbols),
            "by_kind": by_kind,
            "total_scopes": len(self._scopes),
            "total_dependencies": sum(len(deps) for deps in self._dependencies.values()),
        }
