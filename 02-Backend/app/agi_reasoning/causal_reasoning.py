import logging
from typing import Any

logger = logging.getLogger(__name__)


class CausalReasoningService:
    def __init__(self):
        self.graphs: dict[str, Any] = {}

    def add_graph(self, name: str, graph: Any) -> None:
        self.graphs[name] = graph

    def query(self, name: str, query: str) -> dict[str, Any]:
        return {"graph": name, "query": query, "status": "ok"}

    def estimate_effect(self, name: str, treatment: str, outcome: str) -> dict[str, Any]:
        return {"graph": name, "treatment": treatment, "outcome": outcome, "ate": 0.0}
