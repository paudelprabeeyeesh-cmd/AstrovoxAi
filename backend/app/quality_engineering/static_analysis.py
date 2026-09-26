"""Static analysis engine."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AnalysisFinding:
    rule_id: str
    severity: str
    message: str
    file_path: str
    line: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class StaticAnalyzer:
    def __init__(self) -> None:
        self._findings: List[AnalysisFinding] = []

    def analyze(self, file_path: str, content: str) -> List[AnalysisFinding]:
        findings: List[AnalysisFinding] = []
        for idx, line in enumerate(content.splitlines(), start=1):
            if "TODO" in line or "FIXME" in line:
                findings.append(AnalysisFinding(
                    rule_id="todo-fixme",
                    severity="info",
                    message="TODO or FIXME comment found",
                    file_path=file_path,
                    line=idx,
                ))
            if "print(" in line:
                findings.append(AnalysisFinding(
                    rule_id="print-statement",
                    severity="warning",
                    message="Print statement found",
                    file_path=file_path,
                    line=idx,
                ))
        self._findings.extend(findings)
        return findings

    def get_findings(self, severity: Optional[str] = None) -> List[AnalysisFinding]:
        if severity:
            return [f for f in self._findings if f.severity == severity]
        return list(self._findings)


static_analyzer = StaticAnalyzer()
