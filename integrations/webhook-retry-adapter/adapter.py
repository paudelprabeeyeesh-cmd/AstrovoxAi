import json
import time
import logging
import hashlib
import hmac
import requests
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from queue import Queue, Empty

logger = logging.getLogger(__name__)


class DeliveryStatus(Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"


@dataclass
class WebhookEvent:
    event_id: str
    event_type: str
    payload: Dict[str, Any]
    destination_url: str
    secret: Optional[str]
    headers: Dict[str, str] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    attempts: int = 0
    max_attempts: int = 5
    backoff_base: float = 2.0
    status: DeliveryStatus = DeliveryStatus.PENDING
    last_error: Optional[str] = None
    next_attempt_at: Optional[str] = None


@dataclass
class RetryConfig:
    max_attempts: int = 5
    backoff_base: float = 2.0
    backoff_max: float = 60.0
    retryable_statuses: List[int] = field(default_factory=lambda: [429, 500, 502, 503, 504])
    jitter: bool = True


class WebhookRetryAdapter:
    def __init__(self, retry_config: Optional[RetryConfig] = None):
        self.config = retry_config or RetryConfig()
        self._queue: Queue = Queue()
        self._dead_letter: List[WebhookEvent] = []
        self._handlers: Dict[str, Callable] = {}
        self._running = False
        self._session = requests.Session()

    def register_handler(self, event_type: str, handler: Callable[[Dict[str, Any]], Any]):
        self._handlers[event_type] = handler

    def enqueue(self, event: WebhookEvent):
        event.status = DeliveryStatus.PENDING
        self._queue.put(event)
        logger.info(f"Enqueued webhook event {event.event_id} of type {event.event_type}")

    def start(self):
        if self._running:
            return
        self._running = True
        while self._running:
            try:
                event = self._queue.get(timeout=1)
                self._deliver(event)
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Webhook delivery loop error: {e}")

    def stop(self):
        self._running = False

    def _deliver(self, event: WebhookEvent):
        while event.attempts < event.max_attempts and event.status not in [DeliveryStatus.DEAD_LETTER, DeliveryStatus.DELIVERED]:
            event.attempts += 1
            event.status = DeliveryStatus.RETRYING
            try:
                response = self._send(event)
                if response.status_code in self.config.retryable_statuses:
                    wait = self._compute_backoff(event.attempts)
                    logger.warning(f"Webhook {event.event_id} received {response.status_code}, retrying in {wait}s")
                    event.last_error = f"HTTP {response.status_code}"
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                event.status = DeliveryStatus.DELIVERED
                logger.info(f"Webhook {event.event_id} delivered successfully on attempt {event.attempts}")
                self._handle_event(event)
                return
            except requests.RequestException as e:
                event.last_error = str(e)
                if event.attempts >= event.max_attempts:
                    event.status = DeliveryStatus.DEAD_LETTER
                    self._dead_letter.append(event)
                    logger.error(f"Webhook {event.event_id} moved to dead letter queue after {event.attempts} attempts")
                    return
                wait = self._compute_backoff(event.attempts)
                logger.warning(f"Webhook {event.event_id} failed: {e}, retrying in {wait}s")
                time.sleep(wait)

    def _send(self, event: WebhookEvent) -> requests.Response:
        headers = {
            'Content-Type': 'application/json',
            'X-Webhook-Event-Id': event.event_id,
            'X-Webhook-Event-Type': event.event_type,
            'X-Webhook-Attempt': str(event.attempts),
            **event.headers
        }
        if event.secret:
            payload_bytes = json.dumps(event.payload).encode('utf-8')
            signature = hmac.new(event.secret.encode('utf-8'), payload_bytes, hashlib.sha256).hexdigest()
            headers['X-Webhook-Signature'] = f"sha256={signature}"
        return self._session.post(event.destination_url, json=event.payload, headers=headers, timeout=30)

    def _compute_backoff(self, attempt: int) -> float:
        backoff = self.config.backoff_base ** attempt
        if self.config.jitter:
            backoff *= 0.5 + (hash(self._queue.qsize()) % 100) / 200.0
        return min(backoff, self.config.backoff_max)

    def _handle_event(self, event: WebhookEvent):
        handler = self._handlers.get(event.event_type)
        if handler:
            try:
                handler(event.payload)
            except Exception as e:
                logger.error(f"Handler for {event.event_type} failed: {e}")

    def get_dead_letter_queue(self) -> List[WebhookEvent]:
        return list(self._dead_letter)

    def retry_dead_letter(self, event_id: str):
        for event in self._dead_letter:
            if event.event_id == event_id:
                event.attempts = 0
                event.status = DeliveryStatus.PENDING
                event.last_error = None
                self._queue.put(event)
                self._dead_letter.remove(event)
                logger.info(f"Retrying dead letter event {event_id}")
                return True
        return False
