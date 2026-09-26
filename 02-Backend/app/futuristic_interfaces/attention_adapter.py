import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AttentionState:
    focus_score: float = 0.5
    distraction_level: float = 0.0
    effective_focus: float = 0.5
    mode: str = "balanced"
    timestamp: float = field(default_factory=time.time)


class AttentionAwareAdapter:
    def adapt_ui(
        self,
        focus_score: float,
        distraction_signals: list[dict[str, Any]],
        ui_context: dict[str, Any],
    ) -> dict[str, Any]:
        distraction_level = sum(s.get("intensity", 0.0) for s in distraction_signals) / max(len(distraction_signals), 1)
        effective_focus = max(0.0, min(1.0, focus_score - distraction_level * 0.5))

        if effective_focus > 0.75:
            mode = "deep_focus"
            suggestions = ["hide_sidebar", "reduce_notifications", "increase_content_density"]
        elif effective_focus > 0.4:
            mode = "balanced"
            suggestions = ["standard_layout", "adaptive_notifications", "smart_suggestions"]
        else:
            mode = "light_assist"
            suggestions = ["show_guidance", "simplify_choices", "auto_scroll_to_relevant"]

        highlight_intensity = max(0.1, 1.0 - effective_focus)
        notification_mode = "suppress" if effective_focus > 0.7 else "priority_only" if effective_focus > 0.4 else "standard"

        return {
            "mode": mode,
            "effective_focus": round(effective_focus, 3),
            "distraction_level": round(distraction_level, 3),
            "focus_score": round(focus_score, 3),
            "ui_adjustments": {
                "highlight_intensity": round(highlight_intensity, 3),
                "notification_mode": notification_mode,
                "sidebar_visibility": "auto_hide" if effective_focus > 0.7 else "visible",
                "font_size_scale": 1.0 if effective_focus > 0.5 else 1.1,
                "animation_reduction": effective_focus < 0.3,
                "content_density": "high" if effective_focus > 0.7 else "medium" if effective_focus > 0.4 else "low",
            },
            "suggestions": suggestions,
            "timestamp": ui_context.get("timestamp", time.time()),
        }

    def get_state(self, focus_score: float, distraction_signals: list[dict[str, Any]]) -> AttentionState:
        distraction_level = sum(s.get("intensity", 0.0) for s in distraction_signals) / max(len(distraction_signals), 1)
        effective_focus = max(0.0, min(1.0, focus_score - distraction_level * 0.5))
        mode = "deep_focus" if effective_focus > 0.75 else "balanced" if effective_focus > 0.4 else "light_assist"
        return AttentionState(
            focus_score=focus_score,
            distraction_level=distraction_level,
            effective_focus=effective_focus,
            mode=mode,
        )
