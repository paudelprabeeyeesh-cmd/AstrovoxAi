"""Security event webhook dispatcher.

Pushes high-severity security events to external webhook endpoints
in a fire-and-forget manner (with retries and backoff).
"""

from __future__ import annotations

import json
import logging
import threading
import time
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .webhook_signing import WebhookSigner

logger = logging.getLogger(__name__)


@dataclass
class SecurityEvent:
    event_type: str
    severity: str
    user_id: str
    description: str
    timestamp: float
    metadata: Dict[str, Any]


class SecurityEventWebhook:
    """Dispatches security events to configured webhook URLs."""

    def __init__(
        self,
        urls: List[str],
        secret: str,
        timeout_seconds: float = 5.0,
        max_retries: int = 3,
    ) -> None:
        self._urls = [u.strip() for u in urls if u.strip()]
        self._signer = WebhookSigner(secret)
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        self._queue: List[SecurityEvent] = []
        self._lock = threading.Lock()
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False

    def start(self) -> None:
        self._running = True
        self._worker_thread = threading.Thread(target=self._process, daemon=True)
        self._worker_thread.start()

    def stop(self) -> None:
        self._running = False

    def dispatch(self, event: SecurityEvent) -> None:
        with self._lock:
            self._queue.append(event)

    def _process(self) -> None:
        while self._running:
            try:
                with self._lock:
                    if not self._queue:
                        time.sleep(0.5)
                        continue
                    event = self._queue.pop(0)
                self._send(event)
            except Exception:
                logger.exception("Error in security webhook processor")

    def _send(self, event: SecurityEvent) -> None:
        payload = json.dumps({
            "event_type": event.event_type,
            "severity": event.severity,
            "user_id": event.user_id,
            "description": event.description,
            "timestamp": event.timestamp,
            "metadata": event.metadata,
        }).encode("utf-8")
        for url in self._urls:
            for attempt in range(self._max_retries):
                try:
                    req = urllib.request.Request(
                        url,
                        data=payload,
                        headers={
                            "Content-Type": "application/json",
                            "X-Webhook-Signature": self._signer.sign(payload),
                            "X-Security-Event": event.event_type,
                        },
                        method="POST",
                    )
                    with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                        if resp.status < 300:
                            logger.info("Security event dispatched to %s", url)
                            return
                except Exception as exc:
                    logger.warning("Webhook attempt %d failed for %s: %s", attempt + 1, url, exc)
                    time.sleep(2 ** attempt)


security_event_webhook: Optional[SecurityEventWebhook] = None


def init_security_webhook(urls: List[str], secret: str) -> SecurityEventWebhook:
    global security_event_webhook
    security_event_webhook = SecurityEventWebhook(urls, secret)
    security_event_webhook.start()
    return security_event_webhook
