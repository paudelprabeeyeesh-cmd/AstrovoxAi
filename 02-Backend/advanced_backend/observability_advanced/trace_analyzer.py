import statistics
from collections import defaultdict
from typing import Any, Dict, List, Optional

from . import Span


class TraceAnalyzer:
    def __init__(self) -> None:
        self._traces: Dict[str, List[Span]] = defaultdict(list)

    def add_trace(self, trace_id: str, spans: List[Span]) -> None:
        self._traces[trace_id].extend(spans)

    def analyze(self, trace_id: str) -> Dict[str, Any]:
        spans = self._traces.get(trace_id, [])
        if not spans:
            return {"trace_id": trace_id, "span_count": 0}

        durations = [(s.end_time - s.start_time) * 1000 for s in spans if s.end_time is not None]
        return {
            "trace_id": trace_id,
            "span_count": len(spans),
            "duration_stats": {
                "mean": statistics.mean(durations) if durations else None,
                "median": statistics.median(durations) if durations else None,
                "max": max(durations) if durations else None,
                "min": min(durations) if durations else None,
            },
            "operations": [s.name for s in spans],
        }
