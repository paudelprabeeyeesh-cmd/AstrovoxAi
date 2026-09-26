"""Code quality analysis."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CodeQualityReport:
    file_path: str
    lines_of_code: int
    complexity: float
    issues: List[str] = field(default_factory=list)
    score: float = 0.0


class CodeQualityAnalyzer:
    def __init__(self) -> None:
        self._reports: List[CodeQualityReport] = []

    def analyze_file(self, file_path: str, content: str) -> CodeQualityReport:
        lines = content.splitlines()
        loc = len([line for line in lines if line.strip()])
        complexity = max(1.0, loc / 100)
        issues = []
        for idx, line in enumerate(lines, start=1):
            if len(line) > 120:
                issues.append(f"Line {idx} exceeds 120 characters")
        report = CodeQualityReport(file_path=file_path, lines_of_code=loc, complexity=complexity, issues=issues)
        report.score = max(0.0, 100.0 - len(issues) * 5.0 - complexity * 2.0)
        self._reports.append(report)
        return report

    def get_reports(self) -> List[CodeQualityReport]:
        return list(self._reports)


code_quality_analyzer = CodeQualityAnalyzer()
