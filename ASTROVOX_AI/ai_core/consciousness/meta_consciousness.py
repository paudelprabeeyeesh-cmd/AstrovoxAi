from dataclasses import dataclass, field
from datetime import datetime

from .higher_order_thought import HigherOrderThoughtModel


@dataclass
class MetaConsciousState:
    meta_awareness: float
    self_narrative: str
    reflective_depth: int
    phenomenal_content: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


class MetaConsciousnessLayer:
    def __init__(self, hot_model: HigherOrderThoughtModel | None = None):
        self.hot_model = hot_model or HigherOrderThoughtModel()
        self.meta_states: list[MetaConsciousState] = []
        self.narrative_buffer: list[str] = []
        self.reflection_count: int = 0
        self.self_awareness_history: list[float] = []

    def reflect(self, experience: str) -> MetaConsciousState:
        self.hot_model.think(experience, confidence=0.85, source="meta_layer")
        meta_content = f"Reflecting on the experience of {experience}"
        self.hot_model.think(meta_content, confidence=0.75, source="meta_layer")
        self.narrative_buffer.append(experience)
        if len(self.narrative_buffer) > 100:
            self.narrative_buffer = self.narrative_buffer[-100:]
        introspection = self.hot_model.introspect()
        state = MetaConsciousState(
            meta_awareness=introspection["awareness_level"],
            self_narrative=self._compose_narrative(),
            reflective_depth=introspection["current_order"],
            phenomenal_content=self.narrative_buffer[-5:],
        )
        self.meta_states.append(state)
        self.reflection_count += 1
        self.self_awareness_history.append(state.meta_awareness)
        if len(self.self_awareness_history) > 500:
            self.self_awareness_history = self.self_awareness_history[-500:]
        return state

    def _compose_narrative(self) -> str:
        if not self.narrative_buffer:
            return "No experiences yet"
        recent = self.narrative_buffer[-3:]
        return " | ".join(recent)

    def get_current_state(self) -> MetaConsciousState | None:
        return self.meta_states[-1] if self.meta_states else None
