"""Timeline-based systems for conversation, decision trees, and scenario analysis.

Provides:
- Conversation timeline with branching
- Decision tree visualization
- Alternative timeline simulation
- What-if scenario analysis
- Timeline merging and divergence detection
- Causal chain analysis
- Timeline export/import
"""

from __future__ import annotations

import copy
import csv
import io
import json
import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Core types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TimelineNode:
    node_id: str
    parent_node_id: Optional[str]
    content: Dict[str, Any]
    timestamp: datetime
    node_type: str
    branch_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "parent_node_id": self.parent_node_id,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "node_type": self.node_type,
            "branch_id": self.branch_id,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class CausalLink:
    cause_node_id: str
    effect_node_id: str
    relationship: str
    strength: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ScenarioResult:
    scenario_id: str
    branch_id: str
    outcome: Dict[str, Any]
    probability: float
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Conversation timeline
# ---------------------------------------------------------------------------


class ConversationTimeline:
    """Manages conversation history with branching and merging."""

    def __init__(self, conversation_id: str) -> None:
        self._conversation_id = conversation_id
        self._nodes: Dict[str, TimelineNode] = {}
        self._children: Dict[str, List[str]] = {}
        self._branches: Dict[str, str] = {"main": "main"}
        self._lock = threading.Lock()
        self._root = self._add_node(parent_node_id=None, content={}, node_type="root", branch_id="main")

    def _add_node(self, parent_node_id: Optional[str], content: Dict[str, Any], node_type: str, branch_id: str) -> TimelineNode:
        node_id = f"node-{uuid.uuid4().hex[:12]}"
        node = TimelineNode(
            node_id=node_id,
            parent_node_id=parent_node_id,
            content=content,
            timestamp=datetime.now(timezone.utc),
            node_type=node_type,
            branch_id=branch_id,
        )
        with self._lock:
            self._nodes[node_id] = node
            if parent_node_id:
                self._children.setdefault(parent_node_id, []).append(node_id)
        return node

    def add_message(self, role: str, content: str, parent_node_id: Optional[str] = None, branch_id: Optional[str] = None) -> TimelineNode:
        branch = branch_id or "main"
        parent = parent_node_id
        if parent is None:
            all_nodes = [n for n in self._nodes.values() if n.branch_id == branch]
            if all_nodes:
                parent = max(all_nodes, key=lambda n: n.timestamp).node_id
        node = self._add_node(
            parent_node_id=parent,
            content={"role": role, "content": content},
            node_type="message",
            branch_id=branch,
        )
        logger.debug("added message node %s to branch %s", node.node_id, branch)
        return node

    def branch(self, name: str, from_node_id: str) -> str:
        branch_id = f"branch-{uuid.uuid4().hex[:8]}"
        with self._lock:
            self._branches[branch_id] = name
        logger.info("created branch %s from node %s", branch_id, from_node_id)
        return branch_id

    def merge(self, source_branch_id: str, target_branch_id: str, merge_node_id: str) -> TimelineNode:
        with self._lock:
            if source_branch_id not in self._branches and source_branch_id != "main":
                raise ValueError(f"unknown branch: {source_branch_id}")
            if target_branch_id not in self._branches and target_branch_id != "main":
                raise ValueError(f"unknown branch: {target_branch_id}")
        merge_node = self._add_node(
            parent_node_id=merge_node_id,
            content={"action": "merge", "source_branch": source_branch_id, "target_branch": target_branch_id},
            node_type="merge",
            branch_id=target_branch_id,
        )
        logger.info("merged branch %s into %s", source_branch_id, target_branch_id)
        return merge_node

    def detect_divergence(self, branch_a: str, branch_b: str) -> Optional[str]:
        nodes_a = {n.node_id: n for n in self._nodes.values() if n.branch_id == branch_a}
        nodes_b = {n.node_id: n for n in self._nodes.values() if n.branch_id == branch_b}
        for nid in nodes_a:
            if nid in nodes_b:
                return nid
        return None

    def visualize(self, branch_id: Optional[str] = None) -> Dict[str, Any]:
        nodes = [n.to_dict() for n in self._nodes.values() if branch_id is None or n.branch_id == branch_id]
        edges = []
        for n in self._nodes.values():
            if branch_id is None or n.branch_id == branch_id:
                if n.parent_node_id:
                    edges.append({"from": n.parent_node_id, "to": n.node_id})
        return {
            "conversation_id": self._conversation_id,
            "branch_id": branch_id or "all",
            "nodes": nodes,
            "edges": edges,
            "branches": self._branches,
        }

    def get_branch(self, branch_id: str) -> List[Dict[str, Any]]:
        return [n.to_dict() for n in sorted(self._nodes.values(), key=lambda n: n.timestamp) if n.branch_id == branch_id]

    def get_path_to_root(self, node_id: str) -> List[Dict[str, Any]]:
        path = []
        current = self._nodes.get(node_id)
        while current:
            path.append(current.to_dict())
            current = self._nodes.get(current.parent_node_id) if current.parent_node_id else None
        return list(reversed(path))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self._conversation_id,
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "branches": self._branches,
        }


# ---------------------------------------------------------------------------
# Decision tree
# ---------------------------------------------------------------------------


class DecisionTree:
    """Decision tree for what-if analysis and branching scenarios."""

    def __init__(self, tree_id: str) -> None:
        self._tree_id = tree_id
        self._nodes: Dict[str, TimelineNode] = {}
        self._children: Dict[str, List[str]] = {}
        self._lock = threading.Lock()

    def add_decision(self, parent_node_id: Optional[str], content: Dict[str, Any], branch_id: str = "main") -> TimelineNode:
        node_id = f"dec-{uuid.uuid4().hex[:12]}"
        node = TimelineNode(
            node_id=node_id,
            parent_node_id=parent_node_id,
            content=content,
            timestamp=datetime.now(timezone.utc),
            node_type="decision",
            branch_id=branch_id,
        )
        with self._lock:
            self._nodes[node_id] = node
            if parent_node_id:
                self._children.setdefault(parent_node_id, []).append(node_id)
        return node

    def add_outcome(self, parent_decision_id: str, content: Dict[str, Any], branch_id: str = "main") -> TimelineNode:
        node_id = f"out-{uuid.uuid4().hex[:12]}"
        node = TimelineNode(
            node_id=node_id,
            parent_node_id=parent_decision_id,
            content=content,
            timestamp=datetime.now(timezone.utc),
            node_type="outcome",
            branch_id=branch_id,
        )
        with self._lock:
            self._nodes[node_id] = node
            self._children.setdefault(parent_decision_id, []).append(node_id)
        return node

    def visualize(self) -> Dict[str, Any]:
        nodes = [n.to_dict() for n in self._nodes.values()]
        edges = []
        for n in self._nodes.values():
            if n.parent_node_id:
                edges.append({"from": n.parent_node_id, "to": n.node_id})
        return {
            "tree_id": self._tree_id,
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    def get_branches_from(self, node_id: str) -> List[str]:
        return self._children.get(node_id, [])

    def all_paths(self) -> List[List[Dict[str, Any]]]:
        roots = [n for n in self._nodes.values() if n.parent_node_id is None]
        paths = []

        def dfs(node_id: str, path: List[Dict[str, Any]]) -> None:
            node = self._nodes.get(node_id)
            if node is None:
                return
            path.append(node.to_dict())
            children = self._children.get(node_id, [])
            if not children:
                paths.append(list(path))
            else:
                for child in children:
                    dfs(child, path)
            path.pop()

        for root in roots:
            dfs(root.node_id, [])
        return paths


# ---------------------------------------------------------------------------
# Scenario analysis
# ---------------------------------------------------------------------------


class ScenarioAnalyzer:
    """What-if scenario analysis over timelines."""

    def __init__(self, timeline: ConversationTimeline) -> None:
        self._timeline = timeline
        self._scenarios: Dict[str, ScenarioResult] = {}

    def simulate(self, scenario_id: str, branch_id: str, simulation_fn: Callable[[List[Dict[str, Any]]], Dict[str, Any]]) -> ScenarioResult:
        branch_nodes = self._timeline.get_branch(branch_id)
        outcome = simulation_fn(branch_nodes)
        result = ScenarioResult(
            scenario_id=scenario_id,
            branch_id=branch_id,
            outcome=outcome,
            probability=0.0,
        )
        self._scenarios[scenario_id] = result
        logger.info("simulated scenario %s on branch %s", scenario_id, branch_id)
        return result

    def compare_scenarios(self, scenario_a: str, scenario_b: str) -> Dict[str, Any]:
        sa = self._scenarios.get(scenario_a)
        sb = self._scenarios.get(scenario_b)
        if sa is None or sb is None:
            raise ValueError("scenario not found")
        return {
            "scenario_a": scenario_a,
            "scenario_b": scenario_b,
            "outcome_a": sa.outcome,
            "outcome_b": sb.outcome,
            "differences": self._diff_outcomes(sa.outcome, sb.outcome),
        }

    def _diff_outcomes(self, a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "only_in_a": {k: a[k] for k in a if k not in b},
            "only_in_b": {k: b[k] for k in b if k not in a},
            "common": {k: {"a": a[k], "b": b[k]} for k in a if k in b and a[k] != b[k]},
        }

    def list_scenarios(self) -> List[Dict[str, Any]]:
        return [
            {
                "scenario_id": sid,
                "branch_id": s.branch_id,
                "probability": s.probability,
                "outcome": s.outcome,
            }
            for sid, s in self._scenarios.items()
        ]


# ---------------------------------------------------------------------------
# Causal chain analysis
# ---------------------------------------------------------------------------


class CausalChainAnalyzer:
    """Analyzes causal chains over a timeline."""

    def __init__(self, timeline: ConversationTimeline) -> None:
        self._timeline = timeline
        self._links: List[CausalLink] = []

    def add_link(self, cause_node_id: str, effect_node_id: str, relationship: str, strength: float = 1.0) -> None:
        link = CausalLink(cause_node_id=cause_node_id, effect_node_id=effect_node_id, relationship=relationship, strength=strength)
        self._links.append(link)
        logger.debug("added causal link %s -> %s (%s)", cause_node_id, effect_node_id, relationship)

    def analyze(self, start_node_id: str) -> Dict[str, Any]:
        cause_chain: List[Dict[str, Any]] = []
        effect_chain: List[Dict[str, Any]] = []
        queue = [start_node_id]
        visited: set = set()
        while queue:
            nid = queue.pop(0)
            if nid in visited:
                continue
            visited.add(nid)
            node = self._timeline._nodes.get(nid)
            if node:
                cause_chain.append(node.to_dict())
            for link in self._links:
                if link.cause_node_id == nid:
                    effect_chain.append({
                        "link": link.relationship,
                        "strength": link.strength,
                        "node": self._timeline._nodes.get(link.effect_node_id).to_dict() if self._timeline._nodes.get(link.effect_node_id) else None,
                    })
                    queue.append(link.effect_node_id)
        return {
            "start_node_id": start_node_id,
            "cause_chain": cause_chain,
            "effect_chain": effect_chain,
            "link_count": len(self._links),
        }

    def visualize(self) -> Dict[str, Any]:
        nodes = []
        edges = []
        seen: set = set()
        for link in self._links:
            for nid in (link.cause_node_id, link.effect_node_id):
                if nid not in seen:
                    seen.add(nid)
                    node = self._timeline._nodes.get(nid)
                    if node:
                        nodes.append(node.to_dict())
            edges.append({
                "from": link.cause_node_id,
                "to": link.effect_node_id,
                "relationship": link.relationship,
                "strength": link.strength,
            })
        return {"nodes": nodes, "edges": edges}


# ---------------------------------------------------------------------------
# Timeline export / import
# ---------------------------------------------------------------------------


class TimelineExporter:
    """Export and import timelines to/from JSON and CSV."""

    def __init__(self, timeline: ConversationTimeline) -> None:
        self._timeline = timeline

    def to_json(self) -> str:
        return json.dumps(self._timeline.to_dict(), indent=2)

    def to_csv(self) -> str:
        nodes = [n.to_dict() for n in self._timeline._nodes.values()]
        if not nodes:
            return ""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=nodes[0].keys())
        writer.writeheader()
        for node in nodes:
            flat = copy.deepcopy(node)
            flat["content"] = json.dumps(flat.get("content", {}))
            writer.writerow(flat)
        return output.getvalue()

    @classmethod
    def from_json(cls, data: str) -> ConversationTimeline:
        raw = json.loads(data)
        conversation_id = raw.get("conversation_id", "imported")
        timeline = ConversationTimeline(conversation_id=conversation_id)
        for node_data in raw.get("nodes", []):
            timeline._nodes[node_data["node_id"]] = TimelineNode(
                node_id=node_data["node_id"],
                parent_node_id=node_data.get("parent_node_id"),
                content=node_data.get("content", {}),
                timestamp=datetime.fromisoformat(node_data["timestamp"]),
                node_type=node_data.get("node_type", "message"),
                branch_id=node_data.get("branch_id", "main"),
                metadata=node_data.get("metadata", {}),
            )
        return timeline
