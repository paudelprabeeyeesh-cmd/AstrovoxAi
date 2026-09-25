import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class CausalEdge:
    source: str
    target: str
    strength: float = 1.0
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CausalGraph:
    name: str
    nodes: set[str] = field(default_factory=set)
    edges: dict[str, CausalEdge] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


class CausalReasoningService:
    def __init__(self) -> None:
        self._graphs: dict[str, CausalGraph] = {}
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def add_graph(self, name: str, graph: dict[str, Any]) -> dict[str, Any]:
        nodes = set(graph.get("nodes", []))
        edges = {}
        for edge in graph.get("edges", []):
            key = f"{edge.get('source')}->{edge.get('target')}"
            edges[key] = CausalEdge(
                source=edge.get("source", ""),
                target=edge.get("target", ""),
                strength=float(edge.get("strength", 1.0)),
                confidence=float(edge.get("confidence", 1.0)),
                metadata=edge.get("metadata", {}),
            )
        self._graphs[name] = CausalGraph(name=name, nodes=nodes, edges=edges)
        logger.info("Added causal graph %s with %d nodes and %d edges", name, len(nodes), len(edges))
        return {"graph": name, "nodes": len(nodes), "edges": len(edges), "status": "added"}

    def query(self, name: str, query: str) -> dict[str, Any]:
        graph = self._graphs.get(name)
        if not graph:
            return {"graph": name, "status": "not_found"}

        try:
            prompt = (
                "Given the causal graph, answer the query. Return JSON with keys: answer (string), confidence (float 0-1).\n"
                f"Nodes: {list(graph.nodes)}\nEdges: {[{'source': e.source, 'target': e.target, 'strength': e.strength} for e in graph.edges.values()]}\n"
                f"Query: {query}"
            )
            client = self._get_client()
            response = client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            import json
            content = response.choices[0].message.content or "{}"
            data = json.loads(content)
            return {"graph": name, "query": query, "answer": data.get("answer"), "confidence": float(data.get("confidence", 0.0)), "status": "ok"}
        except Exception as exc:
            logger.error("Query failed: %s", exc)
            return {"graph": name, "query": query, "status": "error", "error": str(exc)}

    def estimate_effect(self, name: str, treatment: str, outcome: str) -> dict[str, Any]:
        graph = self._graphs.get(name)
        if not graph:
            return {"graph": name, "treatment": treatment, "outcome": outcome, "ate": 0.0, "status": "not_found"}

        paths = self._find_causal_paths(graph, treatment, outcome)
        direct = any(len(p) == 2 for p in paths)
        ate = self._compute_ate(graph, treatment, outcome, paths)

        return {
            "graph": name,
            "treatment": treatment,
            "outcome": outcome,
            "ate": round(ate, 4),
            "direct": direct,
            "paths_count": len(paths),
            "status": "ok",
        }

    def add_edge(self, graph_name: str, source: str, target: str, strength: float = 1.0, confidence: float = 1.0) -> dict[str, Any]:
        graph = self._graphs.get(graph_name)
        if not graph:
            return {"status": "not_found"}
        key = f"{source}->{target}"
        graph.edges[key] = CausalEdge(source=source, target=target, strength=strength, confidence=confidence)
        graph.nodes.add(source)
        graph.nodes.add(target)
        return {"graph": graph_name, "edge": key, "status": "added"}

    def remove_edge(self, graph_name: str, source: str, target: str) -> dict[str, Any]:
        graph = self._graphs.get(graph_name)
        if not graph:
            return {"status": "not_found"}
        key = f"{source}->{target}"
        graph.edges.pop(key, None)
        return {"graph": graph_name, "edge": key, "status": "removed"}

    def get_graph(self, name: str) -> dict[str, Any] | None:
        graph = self._graphs.get(name)
        if not graph:
            return None
        return {
            "name": graph.name,
            "nodes": list(graph.nodes),
            "edges": [
                {"source": e.source, "target": e.target, "strength": e.strength, "confidence": e.confidence}
                for e in graph.edges.values()
            ],
            "created_at": graph.created_at,
        }

    def list_graphs(self) -> list[str]:
        return list(self._graphs.keys())

    def _find_causal_paths(self, graph: CausalGraph, source: str, target: str, max_paths: int = 10) -> list[list[str]]:
        paths: list[list[str]] = []
        visited: set[str] = set()

        def dfs(current: str, path: list[str]) -> None:
            if len(paths) >= max_paths:
                return
            if current == target:
                paths.append(list(path))
                return
            visited.add(current)
            for edge in graph.edges.values():
                if edge.source == current and edge.target not in visited:
                    path.append(edge.target)
                    dfs(edge.target, path)
                    path.pop()
            visited.discard(current)

        if source in graph.nodes:
            dfs(source, [source])
        return paths

    def _compute_ate(self, graph: CausalGraph, treatment: str, outcome: str, paths: list[list[str]]) -> float:
        if not paths:
            return 0.0
        total = 0.0
        for path in paths:
            edge_key = f"{path[0]}->{path[-1]}" if len(path) == 2 else None
            if edge_key and edge_key in graph.edges:
                total += graph.edges[edge_key].strength * graph.edges[edge_key].confidence
            else:
                total += 0.1
        return round(total / len(paths), 4)
