"""Message queue infrastructure with RabbitMQ support."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Callable, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime

import pika
from pika.connection import Connection
from pika.channel import Channel

from app.core.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class Message:
    id: str
    queue: str
    payload: Dict[str, Any]
    headers: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class MessageQueue:
    """RabbitMQ message queue client."""

    def __init__(self) -> None:
        self._config = get_config()
        self._connection: Optional[Connection] = None
        self._channel: Optional[Channel] = None
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Any]] = {}
        self._connect()

    def _connect(self) -> None:
        try:
            params = pika.URLParameters(self._config.rabbitmq.url)
            self._connection = pika.BlockingConnection(params)
            self._channel = self._connection.channel()
            logger.info("Connected to RabbitMQ")
        except Exception as exc:
            logger.error(f"RabbitMQ connection failed: {exc}")
            raise

    def declare_queue(self, queue_name: str, durable: bool = True) -> None:
        if self._channel:
            self._channel.queue_declare(queue=queue_name, durable=durable)

    def publish(self, queue: str, payload: Dict[str, Any], headers: Optional[Dict[str, Any]] = None) -> str:
        message_id = str(uuid.uuid4())
        message = Message(
            id=message_id,
            queue=queue,
            payload=payload,
            headers=headers or {},
        )
        if self._channel:
            self._channel.basic_publish(
                exchange='',
                routing_key=queue,
                body=json.dumps(payload),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    message_id=message_id,
                    headers=headers or {},
                ),
            )
        logger.info(f"Published message {message_id} to {queue}")
        return message_id

    def consume(self, queue: str, handler: Callable[[Dict[str, Any]], Any]) -> None:
        self._handlers[queue] = handler
        if self._channel:
            self._channel.basic_consume(
                queue=queue,
                on_message_callback=self._on_message,
            )

    def _on_message(self, channel: Channel, method, properties, body: bytes) -> None:
        queue = method.routing_key
        try:
            payload = json.loads(body)
            handler = self._handlers.get(queue)
            if handler:
                handler(payload)
            channel.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as exc:
            logger.error(f"Message processing failed: {exc}")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def start_consuming(self) -> None:
        if self._channel:
            self._channel.start_consuming()

    def stop_consuming(self) -> None:
        if self._channel:
            self._channel.stop_consuming()

    def close(self) -> None:
        if self._channel:
            self._channel.close()
        if self._connection:
            self._connection.close()


_mq: Optional[MessageQueue] = None


def get_message_queue() -> MessageQueue:
    global _mq
    if _mq is None:
        _mq = MessageQueue()
    return _mq
