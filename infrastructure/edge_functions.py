"""Edge functions configuration."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing: Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class EdgeFunction:
    function_id: str
    name: str
    runtime: str
    code: str
    triggers: List[str] = field(default_factory=list)


class EdgeFunctionManager:
    def __init__(self) -> None:
        self._functions: Dict[str, EdgeFunction] = {}

    def deploy(self, function: EdgeFunction) -> EdgeFunction:
        self._functions[function.function_id] = function
        return function


edge_function_manager = EdgeFunctionManager()
