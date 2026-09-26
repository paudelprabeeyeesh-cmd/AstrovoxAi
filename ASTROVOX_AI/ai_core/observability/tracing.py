"""AI distributed tracer."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class AITracer:
    def __init__(self) -> None:
        self._spans: Dict[str, Dict[str, Any]] = {}

    def start_span(self, name: str, parent_span_id: Optional[str] = None) -> str:
        span_id = uuid.uuid4().hex
        self._spans[span_id] = {
            "name": name,
            "parent_span_id": parent_span_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        return span_id

    def end_span(self, span_id: str, status: str = "ok") -> None:
        span = self._spans.get(span_id)
        if span:
            span["ended_at"] = datetime.now(timezone.utc).isoformat()
            span["status"] = status


ai_tracer = AITracer()
