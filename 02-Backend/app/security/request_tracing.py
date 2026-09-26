"""Request ID tracing middleware."""

import uuid
import contextvars
from typing import Optional, Dict, Any
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from datetime import datetime, timezone

request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request_id_var.set(request_id)
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


def get_request_id() -> Optional[str]:
    return request_id_var.get()


class RequestTracer:
    _traces: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def start_trace(cls, trace_id: Optional[str] = None) -> str:
        trace_id = trace_id or str(uuid.uuid4())
        cls._traces[trace_id] = {
            "trace_id": trace_id,
            "spans": [],
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        return trace_id

    @classmethod
    def add_span(cls, trace_id: str, span_name: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        trace = cls._traces.get(trace_id)
        if trace:
            trace["spans"].append({
                "name": span_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": metadata or {},
            })

    @classmethod
    def get_trace(cls, trace_id: str) -> Optional[Dict[str, Any]]:
        return cls._traces.get(trace_id)
