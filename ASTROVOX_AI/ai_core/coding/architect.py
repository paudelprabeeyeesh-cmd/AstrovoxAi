"""AI-enhanced architecture advisor."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class AIArchitect:
    def __init__(self, repo_path: str) -> None:
        self.repo_path = os.path.abspath(repo_path)

    def analyze(self, summary: dict[str, Any], deps: dict[str, Any]) -> dict[str, Any]:
        suggestions: list[dict[str, Any]] = []
        if summary.get("total_files", 0) > 100:
            suggestions.append({"message": "Large codebase detected; consider modularization and bounded contexts.", "severity": "medium"})
        circular = deps.get("circular_dependencies", [])
        if circular:
            suggestions.append({"message": "Resolve circular dependencies to improve maintainability.", "severity": "high"})
        dep_count = len(deps.get("dependencies", {}))
        if dep_count > 200:
            suggestions.append({"message": "High coupling detected; consider interface segregation.", "severity": "medium"})
        return {
            "summary": summary,
            "dependencies": deps,
            "suggestions": suggestions,
            "health_score": max(0, 100 - len(suggestions) * 10),
        }
