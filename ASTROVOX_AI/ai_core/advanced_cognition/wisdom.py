from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class WisdomInsight:
    topic: str
    insight: str
    confidence: float
    source: str
    applicability: list[str] = field(default_factory=list)
    counterarguments: list[str] = field(default_factory=list)
    supporting_evidence: list[str] = field(default_factory=list)
    ethical_weight: float = 0.0
    practical_utility: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


class WisdomAccumulation:
    def __init__(self):
        self.insights: list[WisdomInsight] = []
        self.wisdom_graph: dict[str, list[str]] = {}
        self.source_credibility: dict[str, float] = {}
        self.topic_coherence: dict[str, float] = {}
        self.wisdom_principles: list[str] = []
        self.paradox_registry: dict[str, list[str]] = {}

    def add_insight(self, topic: str, insight: str, confidence: float = 0.7, source: str = "accumulated", applicability: list[str] | None = None) -> WisdomInsight:
        utility = self._estimate_utility(insight, topic)
        ethical = self._estimate_ethical_weight(insight, topic)
        wisdom = WisdomInsight(
            topic=topic,
            insight=insight,
            confidence=confidence,
            source=source,
            applicability=applicability or [],
            practical_utility=utility,
            ethical_weight=ethical,
        )
        self.insights.append(wisdom)
        self.wisdom_graph.setdefault(topic, []).append(insight)
        self.source_credibility[source] = self.source_credibility.get(source, 0.5) + 0.02
        self._update_topic_coherence(topic)
        return wisdom

    def retrieve_wisdom(self, topic: str, limit: int = 5, min_confidence: float = 0.4) -> list[WisdomInsight]:
        relevant = [i for i in self.insights if i.topic == topic and i.confidence >= min_confidence]
        relevant.sort(key=lambda i: (i.confidence + i.practical_utility + i.ethical_weight), reverse=True)
        return relevant[:limit]

    def synthesize_wisdom(self, topics: list[str]) -> WisdomInsight | None:
        combined_insights = []
        for topic in topics:
            combined_insights.extend(self.retrieve_wisdom(topic, limit=3))
        if not combined_insights:
            return None
        themes: dict[str, int] = {}
        for insight in combined_insights:
            for word in insight.insight.lower().split():
                themes[word] = themes.get(word, 0) + 1
        common_themes = sorted(themes.items(), key=lambda x: x[1], reverse=True)[:5]
        synthesis_text = " ".join(t for t, _ in common_themes)
        avg_confidence = sum(i.confidence for i in combined_insights) / len(combined_insights)
        avg_utility = sum(i.practical_utility for i in combined_insights) / len(combined_insights)
        return WisdomInsight(
            topic="synthesis:" + "|".join(topics),
            insight=f"Synthesized: {synthesis_text}",
            confidence=avg_confidence * 0.9,
            source="synthesis",
            practical_utility=avg_utility,
        )

    def challenge_wisdom(self, topic: str, counterargument: str) -> WisdomInsight | None:
        relevant = self.retrieve_wisdom(topic, limit=3)
        if not relevant:
            return None
        target = relevant[0]
        target.counterarguments.append(counterargument)
        target.confidence = max(0.1, target.confidence - 0.1)
        return target

    def register_paradox(self, paradox_name: str, statements: list[str]):
        self.paradox_registry[paradox_name] = statements

    def get_wisdom_summary(self) -> dict[str, Any]:
        if not self.insights:
            return {"status": "no_wisdom_accumulated"}
        latest = self.insights[-1]
        return {
            "total_insights": len(self.insights),
            "topics": list(self.wisdom_graph.keys())[:10],
            "avg_confidence": round(sum(i.confidence for i in self.insights) / len(self.insights), 4),
            "avg_utility": round(sum(i.practical_utility for i in self.insights) / len(self.insights), 4),
            "avg_ethical_weight": round(sum(i.ethical_weight for i in self.insights) / len(self.insights), 4),
            "source_credibility": dict(list(self.source_credibility.items())[:5]),
            "paradoxes_registered": list(self.paradox_registry.keys()),
            "topic_coherence": {k: round(v, 4) for k, v in list(self.topic_coherence.items())[:5]},
        }

    def _estimate_utility(self, insight: str, topic: str) -> float:
        action_keywords = ["should", "must", "act", "do", "apply", "use", "implement"]
        utility = sum(1 for kw in action_keywords if kw in insight.lower())
        return min(1.0, 0.3 + 0.1 * utility)

    def _estimate_ethical_weight(self, insight: str, topic: str) -> float:
        ethical_keywords = ["good", "right", "just", "fair", "harm", "benefit", "dignity", "autonomy"]
        weight = sum(1 for kw in ethical_keywords if kw in insight.lower())
        return min(1.0, 0.2 + 0.12 * weight)

    def _update_topic_coherence(self, topic: str):
        topic_insights = [i for i in self.insights if i.topic == topic]
        if len(topic_insights) < 2:
            self.topic_coherence[topic] = 0.5
            return
        confidences = [i.confidence for i in topic_insights]
        avg = sum(confidences) / len(confidences)
        variance = sum((c - avg) ** 2 for c in confidences) / len(confidences)
        coherence = max(0.0, 1.0 - variance)
        self.topic_coherence[topic] = coherence
