"""Query plan analyzer helper."""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("astrovox.query_plan")


class QueryPlanAnalyzer:
    """Analyze database query plans and detect bottlenecks."""

    def __init__(self) -> None:
        self._history: list[dict] = []

    def analyze(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        analysis = {
            "full_scan": self._detect_full_scan(plan),
            "missing_indexes": self._detect_missing_indexes(plan),
            "expensive_operations": self._detect_expensive_operations(plan),
            "estimated_rows": self._extract_estimated_rows(plan),
            "warnings": [],
        }
        if analysis["full_scan"]:
            analysis["warnings"].append("Query performs a full table scan")
        if analysis["missing_indexes"]:
            analysis["warnings"].append("Query is missing optimal indexes")
        if analysis["expensive_operations"]:
            analysis["warnings"].append("Query contains expensive operations")
        self._history.append(analysis)
        return analysis

    def _detect_full_scan(self, plan: Dict[str, Any]) -> bool:
        plan_text = str(plan).lower()
        return any(keyword in plan_text for keyword in ["seq scan", "table scan", "full scan", "all"])

    def _detect_missing_indexes(self, plan: Dict[str, Any]) -> List[str]:
        missing = []
        plan_text = str(plan)
        if "Seq Scan" in plan_text and "index" not in plan_text.lower():
            missing.append("Consider adding an index for sequential scan")
        if "Sort" in plan_text and "Disk" in plan_text:
            missing.append("Sort spills to disk; consider increasing work_mem")
        return missing

    def _detect_expensive_operations(self, plan: Dict[str, Any]) -> List[str]:
        expensive = []
        plan_text = str(plan)
        if "Nested Loop" in plan_text and plan_text.count("Nested Loop") > 3:
            expensive.append("Multiple nested loops detected")
        if "Hash Join" in plan_text:
            expensive.append("Hash join may consume significant memory")
        if "Seq Scan" in plan_text:
            expensive.append("Sequential scan detected")
        return expensive

    def _extract_estimated_rows(self, plan: Dict[str, Any]) -> Optional[int]:
        plan_text = str(plan)
        match = re.search(r"rows[=:]\s*(\d+)", plan_text)
        if match:
            return int(match.group(1))
        return None

    def get_history(self, limit: int = 100) -> list[dict]:
        return self._history[-limit:]


query_plan_analyzer = QueryPlanAnalyzer()
