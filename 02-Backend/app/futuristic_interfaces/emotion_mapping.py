import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class EmotionTheme:
    emotion: str
    primary: str
    accent: str
    background: str
    font_scale: float = 1.0
    animation_intensity: float = 0.5


class EmotionToUIMappingService:
    THEME_MAP = {
        "joy": EmotionTheme("joy", "#f59e0b", "#fbbf24", "linear-gradient(135deg, #fffbeb, #fef3c7)", font_scale=1.05, animation_intensity=0.8),
        "sadness": EmotionTheme("sadness", "#3b82f6", "#60a5fa", "linear-gradient(135deg, #eff6ff, #dbeafe)", font_scale=1.1, animation_intensity=0.2),
        "anger": EmotionTheme("anger", "#ef4444", "#f87171", "linear-gradient(135deg, #fef2f2, #fee2e2)", font_scale=1.0, animation_intensity=0.9),
        "fear": EmotionTheme("fear", "#8b5cf6", "#a78bfa", "linear-gradient(135deg, #f5f3ff, #ede9fe)", font_scale=1.1, animation_intensity=0.3),
        "surprise": EmotionTheme("surprise", "#10b981", "#34d399", "linear-gradient(135deg, #ecfdf5, #d1fae5)", font_scale=1.0, animation_intensity=0.7),
        "disgust": EmotionTheme("disgust", "#84cc16", "#a3e635", "linear-gradient(135deg, #f7fee7, #ecfccb)", font_scale=1.0, animation_intensity=0.4),
        "neutral": EmotionTheme("neutral", "#06b6d4", "#22d3ee", "linear-gradient(135deg, #ecfeff, #cffafe)", font_scale=1.0, animation_intensity=0.5),
    }

    def map_to_ui(self, valence: float, arousal: float, context: dict[str, Any]) -> dict[str, Any]:
        emotion = self._classify(valence, arousal)
        theme = self.THEME_MAP.get(emotion, self.THEME_MAP["neutral"])

        layout_density = "compact" if arousal > 0.7 else "comfortable" if arousal > 0.3 else "spacious"
        motion_intensity = max(0.0, min(1.0, arousal))
        focus_ring_opacity = max(0.2, 1.0 - abs(valence))

        return {
            "emotion": emotion,
            "valence": round(valence, 3),
            "arousal": round(arousal, 3),
            "ui_theme": {
                "primary": theme.primary,
                "accent": theme.accent,
                "background": theme.background,
                "font_scale": theme.font_scale,
                "animation_intensity": theme.animation_intensity,
            },
            "layout_density": layout_density,
            "motion_intensity": round(motion_intensity, 3),
            "focus_ring_opacity": round(focus_ring_opacity, 3),
            "recommended_actions": self._actions(emotion, context),
            "timestamp": time.time(),
        }

    def _classify(self, valence: float, arousal: float) -> str:
        if valence > 0.3 and arousal > 0.5:
            return "joy"
        if valence < -0.3 and arousal > 0.5:
            return "anger"
        if valence < -0.3 and arousal < 0.3:
            return "sadness"
        if valence > 0.3 and arousal < 0.3:
            return "neutral"
        if arousal > 0.7:
            return "fear"
        if arousal > 0.5:
            return "surprise"
        if valence < -0.5:
            return "disgust"
        return "neutral"

    def _actions(self, emotion: str, context: dict[str, Any]) -> list[str]:
        actions = {
            "joy": ["highlight_positive", "increase_interactivity", "show_celebration"],
            "sadness": ["reduce_cognitive_load", "show_support_options", "simplify_navigation"],
            "anger": ["prioritize_quick_actions", "show_calming_cues", "reduce_friction"],
            "fear": ["increase_transparency", "show_reassurance", "simplify_choices"],
            "surprise": ["highlight_changes", "provide_context", "offer_undo"],
            "disgust": ["reduce_sensory_input", "show_clean_interface", "offer_refresh"],
            "neutral": ["balanced_layout", "standard_interactions", "adaptive_suggestions"],
        }
        return actions.get(emotion, actions["neutral"])
