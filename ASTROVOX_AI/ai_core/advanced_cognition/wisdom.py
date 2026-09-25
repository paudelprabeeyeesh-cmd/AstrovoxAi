from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class WisdomInsight:
    topic: str
    insight: str
    confidence: float
    source: str
    timestamp: datetime = field(default_factory=datetime.now)


class WisdomAccumulation:
    def __init__(self):
        self.insights: list[WisdomInsight] = []
        self.wisdom_graph: dict[str, list[str]] = {}

    def add_insight(self, topic: str, insight: str, confidence: float = 0.7) -> WisdomInsight:
        wisdom = WisdomInsight(
            topic=topic, insight=insight, confidence=confidence, source="accumulated"
        )
        self.insights.append(wisdom)
        self.wisdom_graph.setdefault(topic, []).append(insight)
        return wisdom

    def retrieve_wisdom(self, topic: str, limit: int = 5) -> list[WisdomInsight]:
        relevant = [i for i in self.insights if i.topic == topic]
        relevant.sort(key=lambda i: i.confidence, reverse=True)
        return relevant[:limit]

    def get_wisdom_summary(self) -> dict[str, Any]:
        return {
            "total_insights": len(self.insights),
            "topics": list(self.wisdom_graph.keys())[:10],
            "avg_confidence": sum(i.confidence for i in self.insights) / max(len(self.insights), 1),
        }
