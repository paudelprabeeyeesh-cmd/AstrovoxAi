from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class NarrativeEvent:
    event_id: str
    text: str
    start: float
    end: float
    entities: List[str] = field(default_factory=list)
    relations: List[str] = field(default_factory=list)


class NarrativeCompiler:
    def __init__(self):
        self.events: Dict[str, NarrativeEvent] = {}
        self.timeline: List[NarrativeEvent] = []

    def add_event(self, event_id: str, text: str, start: float, end: float, entities: Optional[List[str]] = None, relations: Optional[List[str]] = None) -> None:
        self.events[event_id] = NarrativeEvent(
            event_id=event_id,
            text=text,
            start=start,
            end=end,
            entities=entities or [],
            relations=relations or [],
        )
        self._rebuild()

    def _rebuild(self) -> None:
        self.timeline = sorted(self.events.values(), key=lambda e: (e.start, e.end))

    def resolve_order(self) -> List[str]:
        return [e.event_id for e in self.timeline]

    def filter_by_entity(self, entity: str) -> List[NarrativeEvent]:
        return [e for e in self.timeline if entity in e.entities]

    def summarize(self) -> List[Dict[str, Any]]:
        return [
            {
                "event_id": e.event_id,
                "text": e.text,
                "start": e.start,
                "end": e.end,
                "entities": e.entities,
                "relations": e.relations,
            }
            for e in self.timeline
        ]
