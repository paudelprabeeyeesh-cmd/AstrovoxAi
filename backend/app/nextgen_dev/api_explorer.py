"""API explorer for endpoint documentation."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class EndpointDoc:
    path: str
    method: str
    summary: str
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    responses: Dict[str, Any] = field(default_factory=dict)
    examples: List[Dict[str, Any]] = field(default_factory=list)


class APIExplorer:
    def __init__(self) -> None:
        self._endpoints: Dict[str, EndpointDoc] = {}

    def register(self, doc: EndpointDoc) -> None:
        key = f"{doc.method}:{doc.path}"
        self._endpoints[key] = doc

    def get_endpoint(self, path: str, method: str) -> Optional[EndpointDoc]:
        key = f"{method}:{path}"
        return self._endpoints.get(key)

    def list_endpoints(self) -> List[EndpointDoc]:
        return list(self._endpoints.values())


api_explorer = APIExplorer()
