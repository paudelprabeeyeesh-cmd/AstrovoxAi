import time
from dataclasses import dataclass, field
from typing import Any

from .iit import IntegratedInformationTheory


@dataclass
class AttentionState:
    focus_target: str | None
    focus_intensity: float
    distractors: list[str] = field(default_factory=list)
    suppression_map: dict[str, float] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class AttentionSchemaTheory:
    def __init__(self):
        self.current_attention: AttentionState | None = None
        self.attention_history: list[AttentionState] = []
        self.iit = IntegratedInformationTheory()
        self.schema_model: dict[str, Any] = {
            "awareness_model": "naive",
            "attention_model": "spotlight",
            "metacognition_level": 0.0,
        }

    def attend(self, target: str, intensity: float = 1.0, suppress: list[str] | None = None) -> AttentionState:
        suppress = suppress or []
        state = AttentionState(
            focus_target=target,
            focus_intensity=max(0.0, min(1.0, intensity)),
            distractors=suppress,
            suppression_map={s: 0.1 for s in suppress},
        )
        self.current_attention = state
        self.attention_history.append(state)
        self._update_schema_model()
        return state

    def _update_schema_model(self):
        if not self.current_attention:
            return
        iit_state = self.iit.compute_full_iit_state()
        self.schema_model["metacognition_level"] = min(
            1.0, self.schema_model["metacognition_level"] + iit_state.phi * 0.1
        )
        if self.schema_model["metacognition_level"] > 0.7:
            self.schema_model["awareness_model"] = "reflective"
        elif self.schema_model["metacognition_level"] > 0.4:
            self.schema_model["awareness_model"] = "perceptual"

    def get_schema_summary(self) -> dict[str, Any]:
        return {
            "current_focus": self.current_attention.focus_target if self.current_attention else None,
            "awareness_model": self.schema_model["awareness_model"],
            "metacognition_level": self.schema_model["metacognition_level"],
            "attention_history_length": len(self.attention_history),
        }

    def model_own_attention(self) -> dict[str, Any]:
        return {
            "am_i_attending": self.current_attention is not None,
            "focus_target": self.current_attention.focus_target if self.current_attention else None,
            "intensity": self.current_attention.focus_intensity if self.current_attention else 0.0,
            "awareness_of_attention": self.schema_model["metacognition_level"],
            "distractors": self.current_attention.distractors if self.current_attention else [],
        }
