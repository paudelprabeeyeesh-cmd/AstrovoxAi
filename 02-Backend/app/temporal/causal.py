"""Causal chain analysis.

Provides:
- Causal event tracking
- Causal edge detection
- Causal chain reconstruction
- Causal graph analysis
- Causal impact measurement
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class CausalEdgeType(Enum):
    """Type of causal relationship."""

    CAUSED = "caused"
    TRIGGERED = "triggered"
    ENABLED = "enabled"
    BLOCKED = "blocked"
    PRECEDED = "preceded"


@dataclass
class CausalEvent:
    """Event in a causal chain."""

    event_id: str
    event_type: str
    aggregate_id: str
    version: int
    occurred_at: datetime
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    incoming_edges: List[str] = field(default_factory=list)
    outgoing_edges: List[str] = field(default_factory=list)


@dataclass
class CausalEdge:
    """Causal relationship between events."""

    edge_id: str
    source_event_id: str
    target_event_id: str
    edge_type: CausalEdgeType
    weight: float = 1.0
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CausalChain:
    """Ordered causal chain of events."""

    chain_id: str
    chain_name: str
    events: List[CausalEvent]
    edges: List[CausalEdge]
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "chain_name": self.chain_name,
            "events": [
                {
                    "event_id": e.event_id,
                    "event_type": e.event_type,
                    "aggregate_id": e.aggregate_id,
                    "version": e.version,
                    "occurred_at": e.occurred_at.isoformat(),
                    "payload": e.payload,
                }
                for e in self.events
            ],
            "edges": [
                {
                    "edge_id": edge.edge_id,
                    "source_event_id": edge.source_event_id,
                    "target_event_id": edge.target_event_id,
                    "edge_type": edge.edge_type.value,
                    "weight": edge.weight,
                }
                for edge in self.edges
            ],
            "description": self.description,
        }


class CausalChainAnalyzer:
    """Causal chain analysis engine.

    Provides:
    - Causal event tracking
    - Causal edge detection
    - Causal chain reconstruction
    - Causal graph analysis
    - Causal impact measurement
    """

    def __init__(self) -> None:
        self._events: Dict[str, CausalEvent] = {}
        self._edges: Dict[str, CausalEdge] = {}
        self._chains: Dict[str, CausalChain] = {}
        self._event_index: Dict[str, List[str]] = {}
        self._lock = False

    def add_event(self, event: CausalEvent) -> None:
        self._events[event.event_id] = event
        agg = event.aggregate_id
        self._event_index.setdefault(agg, []).append(event.event_id)

    def add_edge(self, edge: CausalEdge) -> None:
        self._edges[edge.edge_id] = edge
        src = self._events.get(edge.source_event_id)
        tgt = self._events.get(edge.target_event_id)
        if src:
            src.outgoing_edges.append(edge.edge_id)
        if tgt:
            tgt.incoming_edges.append(edge.edge_id)

    def add_events(self, events: List[CausalEvent]) -> None:
        for event in events:
            self.add_event(event)

    def build_chain(
        self,
        chain_id: str,
        chain_name: str,
        event_ids: List[str],
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CausalChain:
        events = [self._events[eid] for eid in event_ids if eid in self._events]
        edge_ids = set()
        for event in events:
            edge_ids.update(event.incoming_edges)
            edge_ids.update(event.outgoing_edges)
        edges = [self._edges[eid] for eid in edge_ids if eid in self._edges]
        chain = CausalChain(
            chain_id=chain_id,
            chain_name=chain_name,
            events=events,
            edges=edges,
            description=description,
            metadata=metadata or {},
        )
        self._chains[chain_id] = chain
        return chain

    def get_event(self, event_id: str) -> Optional[CausalEvent]:
        return self._events.get(event_id)

    def get_events(self, aggregate_id: Optional[str] = None) -> List[CausalEvent]:
        if aggregate_id:
            return [self._events[eid] for eid in self._event_index.get(aggregate_id, []) if eid in self._events]
        return list(self._events.values())

    def get_edge(self, edge_id: str) -> Optional[CausalEdge]:
        return self._edges.get(edge_id)

    def get_edges(self, event_id: Optional[str] = None) -> List[CausalEdge]:
        if event_id:
            event = self._events.get(event_id)
            if not event:
                return []
            return [self._edges[eid] for eid in event.incoming_edges + event.outgoing_edges if eid in self._edges]
        return list(self._edges.values())

    def get_chain(self, chain_id: str) -> Optional[CausalChain]:
        return self._chains.get(chain_id)

    def get_chains(self) -> List[CausalChain]:
        return list(self._chains.values())

    def get_upstream_events(self, event_id: str) -> List[CausalEvent]:
        visited = set()
        result = []
        queue = [self._events.get(event_id)]
        while queue:
            current = queue.pop(0)
            if not current or current.event_id in visited:
                continue
            visited.add(current.event_id)
            for eid in current.incoming_edges:
                edge = self._edges.get(eid)
                if not edge:
                    continue
                upstream = self._events.get(edge.source_event_id)
                if upstream and upstream.event_id not in visited:
                    result.append(upstream)
                    queue.append(upstream)
        return result

    def get_downstream_events(self, event_id: str) -> List[CausalEvent]:
        visited = set()
        result = []
        queue = [self._events.get(event_id)]
        while queue:
            current = queue.pop(0)
            if not current or current.event_id in visited:
                continue
            visited.add(current.event_id)
            for eid in current.outgoing_edges:
                edge = self._edges.get(eid)
                if not edge:
                    continue
                downstream = self._events.get(edge.target_event_id)
                if downstream and downstream.event_id not in visited:
                    result.append(downstream)
                    queue.append(downstream)
        return result

    def analyze_impact(self, event_id: str) -> Dict[str, Any]:
        event = self._events.get(event_id)
        if not event:
            return {"error": "event not found"}

        upstream = self.get_upstream_events(event_id)
        downstream = self.get_downstream_events(event_id)
        inbound = [self._edges[eid] for eid in event.incoming_edges if eid in self._edges]
        outbound = [self._edges[eid] for eid in event.outgoing_edges if eid in self._edges]

        return {
            "event_id": event_id,
            "event_type": event.event_type,
            "upstream_count": len(upstream),
            "downstream_count": len(downstream),
            "inbound_edges": len(inbound),
            "outbound_edges": len(outbound),
            "total_reach": len(set(e.event_id for e in upstream + downstream + [event])),
        }

    def find_root_causes(self, event_id: str) -> List[CausalEvent]:
        upstream = self.get_upstream_events(event_id)
        return [e for e in upstream if not e.incoming_edges]

    def detect_cycles(self) -> List[List[str]]:
        visited = set()
        cycles = []

        def dfs(event_id: str, path: List[str], rec_stack: Set[str]) -> None:
            if event_id in rec_stack:
                cycle_start = path.index(event_id)
                cycles.append(path[cycle_start:] + [event_id])
                return
            if event_id in visited:
                return
            visited.add(event_id)
            rec_stack.add(event_id)
            event = self._events.get(event_id)
            if event:
                for eid in event.outgoing_edges:
                    edge = self._edges.get(eid)
                    if not edge:
                        continue
                    dfs(edge.target_event_id, path + [event_id], rec_stack)
            rec_stack.remove(event_id)

        for event_id in self._events:
            if event_id not in visited:
                dfs(event_id, [], set())

        return cycles

    def to_graph(self) -> Dict[str, Any]:
        nodes = []
        edges = []
        for event_id, event in self._events.items():
            nodes.append({
                "id": event_id,
                "type": event.event_type,
                "aggregate_id": event.aggregate_id,
                "occurred_at": event.occurred_at.isoformat(),
            })
        for edge in self._edges.values():
            edges.append({
                "source": edge.source_event_id,
                "target": edge.target_event_id,
                "type": edge.edge_type.value,
                "weight": edge.weight,
            })
        return {"nodes": nodes, "edges": edges}

    def get_stats(self) -> Dict[str, Any]:
        return {
            "events": len(self._events),
            "edges": len(self._edges),
            "chains": len(self._chains),
            "aggregates": len(self._event_index),
        }


class CausalGraph:
    """High-level causal graph."""""

    def __init__(self) -> None:
        self.analyzer = CausalChainAnalyzer()
        self._lock = False

    def add_event(self, event: CausalEvent) -> None:
        self.analyzer.add_event(event)

    def add_causal_edge(self, edge: CausalEdge) -> None:
        self.analyzer.add_edge(edge)

    def analyze(self, event_id: str) -> Dict[str, Any]:
        return self.analyzer.analyze_impact(event_id)
