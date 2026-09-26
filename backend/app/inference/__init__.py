"""Backend inference performance service layer."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class InferencePerformanceRegistry:
    _registry: Dict[str, Any] = {}

    @classmethod
    def register(cls, name: str, component: Any) -> None:
        cls._registry[name] = component
        logger.debug("Registered inference component: %s", name)

    @classmethod
    def get(cls, name: str) -> Optional[Any]:
        return cls._registry.get(name)

    @classmethod
    def list_components(cls) -> List[str]:
        return list(cls._registry.keys())
