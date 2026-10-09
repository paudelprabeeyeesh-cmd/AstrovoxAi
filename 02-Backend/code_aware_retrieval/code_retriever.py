from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class CodeFile:
    file_path: str
    language: str
    content: str
    symbols: List[str] = field(default_factory=list)


class CodeRetriever:
    def __init__(self) -> None:
        self._files: Dict[str, CodeFile] = {}
        self._symbol_index: Dict[str, List[str]] = {}

    def add_file(self, code_file: CodeFile) -> None:
        self._files[code_file.file_path] = code_file
        for sym in code_file.symbols:
            self._symbol_index.setdefault(sym, []).append(code_file.file_path)

    def get_by_path(self, file_path: str) -> Optional[CodeFile]:
        return self._files.get(file_path)

    def get_by_symbol(self, symbol: str) -> List[CodeFile]:
        paths = self._symbol_index.get(symbol, [])
        return [self._files[p] for p in paths if p in self._files]

    def get_by_language(self, language: str) -> List[CodeFile]:
        return [f for f in self._files.values() if f.language == language]

    def all_files(self) -> List[CodeFile]:
        return list(self._files.values())
