import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


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
            "effective_focus": effective_focus,
            "distraction_level": distraction_level,
            "ui_adjustments": {
                "highlight_intensity": highlight_intensity,
                "notification_mode": notification_mode,
                "sidebar_visibility": "auto_hide" if effective_focus > 0.7 else "visible",
                "font_size_scale": 1.0 if effective_focus > 0.5 else 1.1,
                "animation_reduction": effective_focus < 0.3,
            },
            "suggestions": suggestions,
            "timestamp": ui_context.get("timestamp"),
        }
