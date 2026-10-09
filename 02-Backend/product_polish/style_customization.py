"""
Style Customization - product_polish

Apply and manage UI style customizations (colors, fonts, themes).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class StyleTheme:
    id: str
    name: str
    description: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "meta": self.meta,
            "created_at": self.created_at,
        }


class StyleCustomization:
    """
    Manage style customizations (colors, fonts, theme overrides).

    Thread-safe.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._themes: Dict[str, StyleTheme] = {}
        self._active: Dict[str, Dict[str, Any]] = {}
        self._overrides: Dict[str, Any] = {}

    def register_theme(self, theme: StyleTheme) -> None:
        """Register a style theme by id."""
        with self._lock:
            self._themes[theme.id] = theme

    def get_theme(self, theme_id: str) -> Optional[StyleTheme]:
        """Get a theme by id."""
        with self._lock:
            return self._themes.get(theme_id)

    def list_themes(self) -> List[StyleTheme]:
        """List all registered themes."""
        with self._lock:
            return list(self._themes.values())

    def set_active(self, component: str, style: Dict[str, Any]) -> None:
        """Set the active style overrides for a component."""
        with self._lock:
            self._active[component] = dict(style)

    def get_active(self, component: str) -> Dict[str, Any]:
        """Get the active style overrides for a component."""
        with self._lock:
            return dict(self._active.get(component, {}))

    def set_override(self, key: str, value: Any) -> None:
        """Set a global style override."""
        with self._lock:
            self._overrides[key] = value

    def get_override(self, key: str) -> Any:
        """Get a global style override."""
        with self._lock:
            return self._overrides.get(key)

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of active styles and overrides."""
        with self._lock:
            return {
                "themes": len(self._themes),
                "active_styles": dict(self._active),
                "overrides": dict(self._overrides),
            }

    def reset_active(self, component: str) -> None:
        """Clear active styles for a component."""
        with self._lock:
            self._active.pop(component, None)
