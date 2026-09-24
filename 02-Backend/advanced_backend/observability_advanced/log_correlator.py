import re
from collections import defaultdict
from typing import Any, Dict, List, Optional


class LogCorrelator:
    def __init__(self) -> None:
        self._logs: List[Dict[str, Any]] = []

    def load(self, logs: List[Dict[str, Any]]) -> None:
        self._logs = list(logs)

    def correlate_by_request_id(self) -> Dict[Optional[str], List[Dict[str, Any]]]:
        grouped: Dict[Optional[str], List[Dict[str, Any]]] = defaultdict(list)
        for entry in self._logs:
            request_id = entry.get("request_id")
            grouped[request_id].append(entry)
        return dict(grouped)

    def search(self, pattern: str) -> List[Dict[str, Any]]:
        compiled = re.compile(pattern)
        results = []
        for entry in self._logs:
            if any(compiled.search(str(v)) for v in entry.values() if v is not None):
                results.append(entry)
        return results
