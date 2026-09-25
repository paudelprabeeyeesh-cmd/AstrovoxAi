import logging
from typing import Any

logger = logging.getLogger(__name__)


class EmotionToUIMappingService:
    THEME_MAP = {
        "joy": {"primary": "#f59e0b", "accent": "#fbbf24", "background": "linear-gradient(135deg, #fffbeb, #fef3c7)"},
        "sadness": {"primary": "#3b82f6", "accent": "#60a5fa", "background": "linear-gradient(135deg, #eff6ff, #dbeafe)"},
        "anger": {"primary": "#ef4444", "accent": "#f87171", "background": "linear-gradient(135deg, #fef2f2, #fee2e2)"},
        "fear": {"primary": "#8b5cf6", "accent": "#a78bfa", "background": "linear-gradient(135deg, #f5f3ff, #ede9fe)"},
        "surprise": {"primary": "#10b981", "accent": "#34d399", "background": "linear-gradient(135deg, #ecfdf5, #d1fae5)"},
        "neutral": {"primary": "#06b6d4", "accent": "#22d3ee", "background": "linear-gradient(135deg, #ecfeff, #cffafe)"},
    }

    def map_to_ui(self, valence: float, arousal: float, context: dict[str, Any]) -> dict[str, Any]:
        if valence > 0.3 and arousal > 0.5:
            emotion = "joy"
        elif valence < -0.3 and arousal > 0.5:
            emotion = "anger"
        elif valence < -0.3 and arousal < 0.3:
            emotion = "sadness"
        elif valence > 0.3 and arousal < 0.3:
            emotion = "neutral"
        elif arousal > 0.7:
            emotion = "fear"
        elif arousal > 0.5:
            emotion = "surprise"
        else:
            emotion = "neutral"

        theme = self.THEME_MAP.get(emotion, self.THEME_MAP["neutral"])

        layout_density = "compact" if arousal > 0.7 else "comfortable" if arousal > 0.3 else "spacious"
        motion_intensity = max(0.0, min(1.0, arousal))
        focus_ring_opacity = max(0.2, 1.0 - abs(valence))

        return {
            "emotion": emotion,
            "valence": valence,
            "arousal": arousal,
            "ui_theme": theme,
            "layout_density": layout_density,
            "motion_intensity": motion_intensity,
            "focus_ring_opacity": focus_ring_opacity,
            "recommended_actions": self._actions(emotion, context),
        }

    def _actions(self, emotion: str, context: dict[str, Any]) -> list[str]:
        actions = {
            "joy": ["highlight_positive", "increase_interactivity", "show_celebration"],
            "sadness": ["reduce_cognitive_load", "show_support_options", "simplify_navigation"],
            "anger": ["prioritize_quick_actions", "show_calming_cues", "reduce_friction"],
            "fear": ["increase_transparency", "show_reassurance", "simplify_choices"],
            "surprise": ["highlight_changes", "provide_context", "offer_undo"],
            "neutral": ["balanced_layout", "standard_interactions", "adaptive_suggestions"],
        }
        return actions.get(emotion, actions["neutral"])
