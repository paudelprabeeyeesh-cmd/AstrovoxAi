"""Webhook handlers with retry and signature verification."""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class WebhookEvent:
    event_id: str
    event_type: str
    payload: Dict[str, Any]
    headers: Dict[str, str]
    signature: Optional[str] = None
    received_at: float = field(default_factory=time.time)
    processed: bool = False


@dataclass
class WebhookHandlerResult:
    status_code: int
    body: str
    retry_after: Optional[int] = None


class WebhookHandler:
    """Base webhook handler with signature verification."""

    def __init__(self, secret: str, algorithm: str = "sha256"):
        self._secret = secret
        self._algorithm = algorithm
        self._handlers: Dict[str, Callable] = {}

    def register(self, event_type: str, handler: Callable) -> None:
        self._handlers[event_type] = handler

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        if not signature:
            return False
        expected = hmac.new(self._secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def handle(self, event: WebhookEvent) -> WebhookHandlerResult:
        handler = self._handlers.get(event.event_type)
        if not handler:
            return WebhookHandlerResult(status_code=200, body="ignored")
        try:
            result = handler(event.payload)
            event.processed = True
            return WebhookHandlerResult(status_code=200, body="ok")
        except Exception as exc:  # noqa: BLE001
            logger.error("Webhook handler failed for %s: %s", event.event_type, exc)
            return WebhookHandlerResult(status_code=500, body="error", retry_after=60)


class WebhookDispatcher:
    """Routes incoming webhook payloads to handlers."""

    def __init__(self):
        self._handlers: Dict[str, WebhookHandler] = {}

    def register_handler(self, provider: str, handler: WebhookHandler) -> None:
        self._handlers[provider] = handler

    def dispatch(self, provider: str, event: WebhookEvent) -> WebhookHandlerResult:
        handler = self._handlers.get(provider)
        if not handler:
            return WebhookHandlerResult(status_code=404, body="unknown provider")
        return handler.handle(event)

    def dispatch_raw(self, provider: str, payload: bytes, headers: Dict[str, str]) -> WebhookHandlerResult:
        event_type = headers.get("X-Event-Type", "unknown")
        signature = headers.get("X-Signature-256") or headers.get("X-Hub-Signature-256")
        event = WebhookEvent(
            event_id=headers.get("X-Request-Id", ""),
            event_type=event_type,
            payload={},
            headers=headers,
            signature=signature,
        )
        return self.dispatch(provider, event)


webhook_dispatcher = WebhookDispatcher()
