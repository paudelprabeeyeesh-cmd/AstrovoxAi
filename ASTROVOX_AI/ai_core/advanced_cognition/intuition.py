from dataclasses import dataclass, field
from typing import Any


@dataclass
class IntuitionSignal:
    pattern: str
    confidence: float
    source: str
    timestamp: float


class IntuitionSimulation:
    def __init__(self):
        self.pattern_library: dict[str, float] = {}
        self.signal_history: list[IntuitionSignal] = []

    def register_pattern(self, pattern: str, confidence: float = 0.7):
        self.pattern_library[pattern] = max(0.0, min(1.0, confidence))

    def intuit(self, context: str) -> IntuitionSignal | None:
        best_pattern = None
        best_score = 0.0
        for pattern, confidence in self.pattern_library.items():
            if pattern.lower() in context.lower() and confidence > best_score:
                best_pattern = pattern
                best_score = confidence
        if not best_pattern:
            return None
        signal = IntuitionSignal(
            pattern=best_pattern,
            confidence=best_score,
            source="pattern_matching",
            timestamp=__import__("time").time(),
        )
        self.signal_history.append(signal)
        return signal

    def get_intuition_summary(self) -> dict[str, Any]:
        return {
            "patterns_registered": len(self.pattern_library),
            "recent_signals": [s.pattern for s in self.signal_history[-5:]],
        }
