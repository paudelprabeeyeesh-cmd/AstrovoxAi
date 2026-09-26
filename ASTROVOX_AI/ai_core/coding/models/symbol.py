"""Symbol model for code entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Symbol:
    name: str
    kind: str
    file_path: str
    line: int
    end_line: int
    signature: str = ""
    docstring: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
