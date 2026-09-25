from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class ArchitectureRule:
    name: str
    description: str
    severity: str = "error"
    enabled: bool = True


@dataclass
class ArchitectureRuleset:
    rules: List[ArchitectureRule] = field(default_factory=list)

    @classmethod
    def default(cls) -> ArchitectureRuleset:
        return cls(
            rules=[
                ArchitectureRule(
                    name="no-cycles",
                    description="No circular dependencies between app modules",
                ),
                ArchitectureRule(
                    name="naming-convention",
                    description="Modules must use snake_case filenames",
                ),
                ArchitectureRule(
                    name="no-absolute-imports-in-tests",
                    description="Tests must use relative imports within test directories",
                ),
            ]
        )
