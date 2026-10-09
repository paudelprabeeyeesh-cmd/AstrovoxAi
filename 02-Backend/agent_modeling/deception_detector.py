import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Statement:
    claim: str
    confidence: float
    timestamp: float
    consistency_score: float = 1.0
    topic: str = ""


@dataclass
class DeceptionSignal:
    signal_type: str
    severity: float
    description: str


@dataclass
class DeceptionReport:
    risk_score: float
    signals: List[DeceptionSignal]
    confidence: float


class DeceptionDetector:
    def __init__(self, history_size: int = 200, contradiction_threshold: float = 0.4):
        self.history_size = history_size
        self.statements: List[Statement] = []
        self.topic_claims: Dict[str, List[Statement]] = {}
        self.contradiction_threshold: float = contradiction_threshold

    def record_statement(self, statement: Statement) -> None:
        self.statements.append(statement)
        if len(self.statements) > self.history_size:
            self.statements = self.statements[-self.history_size :]
        topic = statement.topic or "__default__"
        if topic not in self.topic_claims:
            self.topic_claims[topic] = []
        self.topic_claims[topic].append(statement)
        if len(self.topic_claims[topic]) > self.history_size:
            self.topic_claims[topic] = self.topic_claims[topic][-self.history_size :]

    def check_consistency(self, topic: str) -> float:
        topic = topic or "__default__"
        if topic not in self.topic_claims or len(self.topic_claims[topic]) < 2:
            return 1.0
        claims = self.topic_claims[topic]
        confidences = [c.confidence for c in claims]
        avg_conf = sum(confidences) / len(confidences)
        variance = sum((c - avg_conf) ** 2 for c in confidences) / len(confidences)
        return max(0.0, 1.0 - math.sqrt(variance))

    def detect_contradictions(self, topic: str) -> List[DeceptionSignal]:
        topic = topic or "__default__"
        signals = []
        if topic not in self.topic_claims or len(self.topic_claims[topic]) < 2:
            return signals
        claims = self.topic_claims[topic]
        for i in range(len(claims)):
            for j in range(i + 1, len(claims)):
                sim = self._claim_similarity(claims[i].claim, claims[j].claim)
                if sim < self.contradiction_threshold and abs(claims[i].confidence - claims[j].confidence) > 0.5:
                    severity = max(0.0, 1.0 - sim)
                    signals.append(
                        DeceptionSignal(
                            signal_type="contradiction",
                            severity=severity,
                            description=f"Contradictory claims on {topic}: '{claims[i].claim}' vs '{claims[j].claim}'",
                        )
                    )
        return signals

    def calculate_risk_score(self, topic: str) -> float:
        consistency = self.check_consistency(topic)
        contradictions = self.detect_contradictions(topic)
        if not contradictions:
            return max(0.0, 1.0 - consistency)
        max_severity = max(c.severity for c in contradictions)
        return min(1.0, max_severity * 0.7 + (1.0 - consistency) * 0.3)

    def generate_report(self, topic: str) -> DeceptionReport:
        signals = self.detect_contradictions(topic)
        consistency = self.check_consistency(topic)
        risk = self.calculate_risk_score(topic)
        return DeceptionReport(risk_score=risk, signals=signals, confidence=consistency)

    def _claim_similarity(self, claim_a: str, claim_b: str) -> float:
        words_a = set(claim_a.lower().split())
        words_b = set(claim_b.lower().split())
        if not words_a and not words_b:
            return 1.0
        intersection = words_a.intersection(words_b)
        union = words_a.union(words_b)
        return len(intersection) / len(union) if union else 0.0
