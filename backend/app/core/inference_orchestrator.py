"""Backend app core inference orchestration."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class InferenceOrchestrator:
    def __init__(self):
        self._components: Dict[str, Any] = {}

    def register(self, name: str, component: Any) -> None:
        self._components[name] = component
        logger.debug("Registered core component: %s", name)

    def get(self, name: str) -> Optional[Any]:
        return self._components.get(name)

    def list_components(self) -> List[str]:
        return list(self._components.keys())

    def health_check(self) -> Dict[str, Any]:
        return {
            "registered_components": len(self._components),
            "components": self.list_components(),
        }


inference_orchestrator = InferenceOrchestrator()
