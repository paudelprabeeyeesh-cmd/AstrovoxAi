from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Symbol:
    name: str
    kind: str
    file_path: str
    line: int
    column: int = 0
    signature: Optional[str] = None


class SymbolIndexer:
    def __init__(self) -> None:
        self._symbols: List[Symbol] = []
        self._by_name: Dict[str, List[Symbol]] = {}

    def add_symbol(self, symbol: Symbol) -> None:
        self._symbols.append(symbol)
        self._by_name.setdefault(symbol.name, []).append(symbol)

    def get_by_name(self, name: str) -> List[Symbol]:
        return list(self._by_name.get(name, []))

    def get_by_kind(self, kind: str) -> List[Symbol]:
        return [s for s in self._symbols if s.kind == kind]

    def get_by_file(self, file_path: str) -> List[Symbol]:
        return [s for s in self._symbols if s.file_path == file_path]

    def all_symbols(self) -> List[Symbol]:
        return list(self._symbols)
