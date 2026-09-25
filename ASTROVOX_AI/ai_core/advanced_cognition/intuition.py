from dataclasses import dataclass, field
from typing import Any
import time
import random


@dataclass
class IntuitionSignal:
    pattern: str
    confidence: float
    source: str
    emotional_valence: float = 0.0
    somatic_marker: str = ""
    implicit_memory_trace: str = ""
    gut_feeling_strength: float = 0.0
    timestamp: float = field(default_factory=time.time)


class IntuitionSimulation:
    def __init__(self):
        self.pattern_library: dict[str, dict[str, Any]] = {}
        self.signal_history: list[IntuitionSignal] = []
        self.implicit_memory: list[dict[str, Any]] = []
        self.somatic_markers: dict[str, float] = {}
        self.heuristics: dict[str, float] = {}
        self.affective_associations: dict[str, float] = {}
        self.context_window: list[str] = []
        self.max_context_size: int = 50

    def register_pattern(self, pattern: str, confidence: float = 0.7, emotional_valence: float = 0.0, somatic_marker: str = ""):
        self.pattern_library[pattern] = {
            "confidence": max(0.0, min(1.0, confidence)),
            "emotional_valence": max(-1.0, min(1.0, emotional_valence)),
            "somatic_marker": somatic_marker,
            "access_count": self.pattern_library.get(pattern, {}).get("access_count", 0) + 1,
        }
        if somatic_marker:
            self.somatic_markers[somatic_marker] = self.somatic_markers.get(somatic_marker, 0.0) + 0.1

    def intuit(self, context: str, mode: str = "fast") -> IntuitionSignal | None:
        self._update_context_window(context)
        best_pattern = None
        best_score = 0.0
        context_lower = context.lower()
        for pattern, data in self.pattern_library.items():
            if pattern.lower() in context_lower:
                recency_boost = 1.0 + 0.1 * min(data.get("access_count", 1), 10)
                score = data["confidence"] * recency_boost
                if score > best_score:
                    best_pattern = pattern
                    best_score = score
        if not best_pattern:
            return self._implicit_intuition(context)
        data = self.pattern_library[best_pattern]
        signal = IntuitionSignal(
            pattern=best_pattern,
            confidence=best_score,
            source="pattern_matching",
            emotional_valence=data.get("emotional_valence", 0.0),
            somatic_marker=data.get("somatic_marker", ""),
            gut_feeling_strength=min(1.0, best_score * 0.9),
        )
        self.signal_history.append(signal)
        return signal

    def implicit_intuition(self, context: str) -> IntuitionSignal | None:
        return self._implicit_intuition(context)

    def heuristic_processing(self, context: str) -> dict[str, Any]:
        signals = []
        for heuristic, weight in self.heuristics.items():
            if heuristic.lower() in context.lower():
                signals.append({"heuristic": heuristic, "weight": weight})
        signals.sort(key=lambda s: s["weight"], reverse=True)
        return {
            "active_heuristics": signals[:5],
            "intuition_mode": "heuristic",
            "confidence": signals[0]["weight"] if signals else 0.0,
        }

    def register_heuristic(self, heuristic: str, weight: float = 0.7):
        self.heuristics[heuristic] = max(0.0, min(1.0, weight))

    def affective_intuition(self, context: str) -> dict[str, Any]:
        context_lower = context.lower()
        associations = []
        for trigger, valence in self.affective_associations.items():
            if trigger.lower() in context_lower:
                associations.append({"trigger": trigger, "valence": valence})
        associations.sort(key=lambda a: abs(a["valence"]), reverse=True)
        return {
            "affective_signals": associations[:5],
            "emotional_tone": associations[0]["valence"] if associations else 0.0,
            "intuition_mode": "affective",
        }

    def register_affective_association(self, trigger: str, valence: float):
        self.affective_associations[trigger] = max(-1.0, min(1.0, valence))

    def get_intuition_summary(self) -> dict[str, Any]:
        recent = self.signal_history[-10:]
        return {
            "patterns_registered": len(self.pattern_library),
            "recent_signals": [s.pattern for s in recent],
            "avg_confidence": sum(s.confidence for s in recent) / max(len(recent), 1),
            "somatic_markers_active": len(self.somatic_markers),
            "heuristics_active": len(self.heuristics),
            "affective_triggers": len(self.affective_associations),
            "context_window_size": len(self.context_window),
        }

    def _implicit_intuition(self, context: str) -> IntuitionSignal | None:
        if not self.implicit_memory:
            return None
        context_words = set(context.lower().split())
        best_trace = None
        best_overlap = 0
        for trace in self.implicit_memory:
            trace_words = set(trace.get("content", "").lower().split())
            overlap = len(context_words & trace_words)
            if overlap > best_overlap:
                best_overlap = overlap
                best_trace = trace
        if not best_trace or best_overlap == 0:
            return None
        signal = IntuitionSignal(
            pattern="implicit_recall",
            confidence=0.4 + 0.3 * (best_overlap / max(len(context_words), 1)),
            source="implicit_memory",
            implicit_memory_trace=best_trace.get("content", "")[:100],
            gut_feeling_strength=0.35 + 0.25 * random.random(),
        )
        self.signal_history.append(signal)
        return signal

    def _update_context_window(self, context: str):
        self.context_window.append(context)
        if len(self.context_window) > self.max_context_size:
            self.context_window.pop(0)
