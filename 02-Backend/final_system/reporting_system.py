"""
Reporting system with dashboards and report generation.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Report:
    title: str
    data: Dict[str, Any]
    generated_at: str = ""

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.utcnow().isoformat()


class ReportingSystem:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._reports: Dict[str, Report] = {}
        self._dashboards: Dict[str, List[str]] = {}

    def generate_report(self, report: Report) -> None:
        with self._lock:
            self._reports[report.title] = report

    def get_report(self, title: str) -> Optional[Report]:
        return self._reports.get(title)

    def register_dashboard(self, name: str, report_titles: List[str]) -> None:
        with self._lock:
            self._dashboards[name] = report_titles

    def dashboard(self, name: str) -> Dict[str, Optional[Report]]:
        with self._lock:
            titles = self._dashboards.get(name, [])
        return {title: self._reports.get(title) for title in titles}

    def list_reports(self) -> List[str]:
        with self._lock:
            return list(self._reports.keys())

    def list_dashboards(self) -> List[str]:
        with self._lock:
            return list(self._dashboards.keys())
