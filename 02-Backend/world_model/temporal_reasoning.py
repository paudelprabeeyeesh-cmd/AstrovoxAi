from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


@dataclass
class Event:
    id: str
    timestamp: float
    description: str
    entities: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CausalLink:
    cause: str
    effect: str
    strength: float = 0.5
    delay: float = 0.0


class TemporalReasoner:
    def __init__(self):
        self.events: List[Event] = []
        self.links: List[CausalLink] = []

    def add_event(self, event: Event) -> None:
        self.events.append(event)
        self.events.sort(key=lambda e: e.timestamp)

    def add_causal_link(self, cause: str, effect: str, strength: float = 0.5, delay: float = 0.0) -> None:
        self.links.append(CausalLink(cause=cause, effect=effect, strength=strength, delay=delay))

    def sequence(self, start_time: float, end_time: float) -> List[Event]:
        return [e for e in self.events if start_time <= e.timestamp <= end_time]

    def causality_score(self, event_a: str, event_b: str) -> float:
        link = next((l for l in self.links if l.cause == event_a and l.effect == event_b), None)
        return link.strength if link else 0.0

    def predict_next(self, window: int = 3) -> Optional[Event]:
        if not self.events:
            return None
        recent = self.events[-window:]
        last = recent[-1]
        predicted_time = last.timestamp + 1.0
        return Event(id=f"pred_{predicted_time}", timestamp=predicted_time, description="predicted_event")

    def build_timeline(self) -> List[Dict[str, Any]]:
        timeline = []
        for event in self.events:
            causes = [l.cause for l in self.links if l.effect == event.id]
            timeline.append({
                "event": event.id,
                "time": event.timestamp,
                "description": event.description,
                "causes": causes,
            })
        return timeline

    def event_similarity(self, a: Event, b: Event) -> float:
        entity_overlap = len(set(a.entities) & set(b.entities)) / max(len(set(a.entities) | set(b.entities)), 1)
        time_dist = abs(a.timestamp - b.timestamp)
        return float(0.5 * entity_overlap + 0.5 * np.exp(-time_dist))
