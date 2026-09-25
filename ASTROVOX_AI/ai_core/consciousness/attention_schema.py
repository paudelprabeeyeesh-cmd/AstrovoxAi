import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AttentionFocus:
    target: str
    intensity: float = 1.0
    duration: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class AttentionSchema:
    def __init__(self):
        self.current_focus: AttentionFocus | None = None
        self.attention_history: list[AttentionFocus] = []
        self.schema_model: dict[str, Any] = {
            "focus_state": "idle",
            "capacity_remaining": 1.0,
            "distraction_level": 0.0,
        }

    def attend(self, target: str, intensity: float = 1.0) -> dict[str, Any]:
        if self.current_focus and self.current_focus.intensity > intensity:
            self.attention_history.append(self.current_focus)

        self.current_focus = AttentionFocus(target=target, intensity=intensity)
        self.schema_model["focus_state"] = "focused"
        self.schema_model["capacity_remaining"] = max(0.0, 1.0 - intensity * 0.3)

        logger.info("Attention focused on: %s (%.2f)", target, intensity)
        return {"status": "attended", "target": target, "intensity": intensity}

    def shift(self, new_target: str) -> dict[str, Any]:
        if self.current_focus:
            self.current_focus.duration = 1.0
            self.attention_history.append(self.current_focus)

        self.current_focus = AttentionFocus(target=new_target)
        self.schema_model["focus_state"] = "shifted"
        logger.info("Attention shifted to: %s", new_target)
        return {"status": "shifted", "new_target": new_target}

    def get_schema_report(self) -> dict[str, Any]:
        return {
            "schema_model": self.schema_model,
            "current_focus": {
                "target": self.current_focus.target if self.current_focus else None,
                "intensity": self.current_focus.intensity if self.current_focus else 0.0,
            },
            "history_length": len(self.attention_history),
        }

    def control_attention(self, stimulus: str, relevance: float) -> dict[str, Any]:
        if relevance > 0.7:
            return self.attend(stimulus, intensity=min(relevance, 1.0))
        if self.current_focus and relevance < 0.3:
            return self.shift(stimulus)
        return {"status": "ignored", "stimulus": stimulus}
