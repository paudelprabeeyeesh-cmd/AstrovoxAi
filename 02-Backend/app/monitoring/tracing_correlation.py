"""Correlation ID tracking for distributed tracing."""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
import threading


@dataclass
class CorrelationContext:
    correlation_id: str
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


class CorrelationManager:
    _contexts: Dict[str, CorrelationContext] = {}
    _thread_local = threading.local()

    @classmethod
    def generate_correlation_id(cls) -> str:
        return str(uuid.uuid4())

    @classmethod
    def generate_trace_id(cls) -> str:
        return uuid.uuid4().hex

    @classmethod
    def generate_span_id(cls) -> str:
        return uuid.uuid4().hex[:16]

    @classmethod
    def create_context(cls, user_id: Optional[str] = None,
                       session_id: Optional[str] = None,
                       parent_correlation_id: Optional[str] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> CorrelationContext:
        correlation_id = parent_correlation_id or cls.generate_correlation_id()
        trace_id = cls.generate_trace_id()
        span_id = cls.generate_span_id()

        context = CorrelationContext(
            correlation_id=correlation_id,
            trace_id=trace_id,
            span_id=span_id,
            user_id=user_id,
            session_id=session_id,
            metadata=metadata or {}
        )

        cls._contexts[correlation_id] = context
        cls.set_thread_context(context)
        return context

    @classmethod
    def create_child_span(cls, parent_correlation_id: str,
                          name: str,
                          metadata: Optional[Dict[str, Any]] = None) -> Optional[CorrelationContext]:
        parent = cls._contexts.get(parent_correlation_id)
        if not parent:
            return None

        child = CorrelationContext(
            correlation_id=parent.correlation_id,
            trace_id=parent.trace_id,
            span_id=cls.generate_span_id(),
            parent_span_id=parent.span_id,
            user_id=parent.user_id,
            session_id=parent.session_id,
            metadata={**parent.metadata, **(metadata or {}), "child_span": name}
        )

        cls._contexts[parent.correlation_id] = child
        cls.set_thread_context(child)
        return child

    @classmethod
    def get_context(cls, correlation_id: str) -> Optional[CorrelationContext]:
        return cls._contexts.get(correlation_id)

    @classmethod
    def set_thread_context(cls, context: CorrelationContext) -> None:
        cls._thread_local.context = context

    @classmethod
    def get_thread_context(cls) -> Optional[CorrelationContext]:
        return getattr(cls._thread_local, 'context', None)

    @classmethod
    def get_correlation_id(cls) -> Optional[str]:
        context = cls.get_thread_context()
        return context.correlation_id if context else None

    @classmethod
    def get_trace_id(cls) -> Optional[str]:
        context = cls.get_thread_context()
        return context.trace_id if context else None

    @classmethod
    def get_span_id(cls) -> Optional[str]:
        context = cls.get_thread_context()
        return context.span_id if context else None

    @classmethod
    def get_user_id(cls) -> Optional[str]:
        context = cls.get_thread_context()
        return context.user_id if context else None

    @classmethod
    def enrich_with_request(cls, correlation_id: str, request_data: Dict[str, Any]) -> None:
        context = cls._contexts.get(correlation_id)
        if context:
            context.metadata.update(request_data)

    @classmethod
    def get_full_context(cls, correlation_id: str) -> Dict[str, Any]:
        context = cls._contexts.get(correlation_id)
        if not context:
            return {}
        return {
            "correlation_id": context.correlation_id,
            "trace_id": context.trace_id,
            "span_id": context.span_id,
            "parent_span_id": context.parent_span_id,
            "user_id": context.user_id,
            "session_id": context.session_id,
            "created_at": context.created_at.isoformat(),
            "metadata": context.metadata
        }

    @classmethod
    def clear_expired_contexts(cls, max_age_seconds: int = 3600) -> int:
        now = datetime.now(timezone.utc)
        expired = []
        for cid, ctx in cls._contexts.items():
            age = (now - ctx.created_at).total_seconds()
            if age > max_age_seconds:
                expired.append(cid)
        for cid in expired:
            del cls._contexts[cid]
        return len(expired)
