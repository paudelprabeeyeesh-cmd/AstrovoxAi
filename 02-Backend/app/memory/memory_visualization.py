"""
Memory Visualization - Provides data structures for memory visualization.

Generates:
- Memory distribution charts
- Timeline data
- Relationship graphs
- Heatmaps
- Usage statistics
"""

from typing import Any, Dict, List, Optional
from datetime import datetime


class MemoryVisualization:
    """Prepares memory data for visualization."""

    def __init__(self):
        self._events: List[Dict[str, Any]] = []

    def record_event(self, event_type: str, layer: str, metadata: Optional[Dict[str, Any]] = None):
        self._events.append({
            "event_type": event_type,
            "layer": layer,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
        })

    def timeline(self, user_id: str, start: Optional[str] = None, end: Optional[str] = None) -> List[Dict[str, Any]]:
        events = []
        for ev in self._events:
            ts = ev.get("timestamp", "")
            if start and ts < start:
                continue
            if end and ts > end:
                continue
            events.append(ev)
        events.sort(key=lambda e: e.get("timestamp", ""))
        return events

    def layer_distribution(self, counts: Dict[str, int]) -> Dict[str, Any]:
        total = sum(counts.values()) if counts else 0
        return {
            "total": total,
            "distribution": {k: {"count": v, "percentage": v / total if total else 0.0} for k, v in counts.items()},
        }

    def memory_heatmap(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        grid: Dict[str, int] = {}
        for mem in memories:
            ts = mem.get("created_at", "")[:10]
            grid[ts] = grid.get(ts, 0) + 1
        return [{"date": k, "count": v} for k, v in sorted(grid.items())]

    def relationship_graph(self, relations: List[Dict[str, Any]]) -> Dict[str, Any]:
        nodes = {}
        edges = []
        for rel in relations:
            source = rel.get("source", "")
            target = rel.get("target", "")
            nodes.setdefault(source, {"id": source, "label": source})
            nodes.setdefault(target, {"id": target, "label": target})
            edges.append({"source": source, "target": target, "type": rel.get("type", "related")})
        return {"nodes": list(nodes.values()), "edges": edges}
