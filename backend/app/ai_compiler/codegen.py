"""Code generator for AI compiler."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class GeneratedCode:
    language: str
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CodeGenerator:
    def __init__(self) -> None:
        self._generated: List[GeneratedCode] = []

    def generate(self, language: str, ir: Dict[str, Any]) -> GeneratedCode:
        source = f"# Generated {language} code\n"
        code = GeneratedCode(language=language, source=source, metadata={"ir": ir})
        self._generated.append(code)
        return code

    def get_generated(self) -> List[GeneratedCode]:
        return list(self._generated)


code_generator = CodeGenerator()
