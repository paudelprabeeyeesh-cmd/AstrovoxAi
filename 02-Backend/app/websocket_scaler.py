
import json
import logging
import uuid
from typing import AsyncGenerator

import redis

logger = logging.getLogger(__name__)


class WebSocketScaler:
    def __init__(self, redis_url: str = None):
        url = redis_url or "redis://localhost:6379"
        self._redis = redis.Redis.from_url(url, decode_responses=True)
        self._pubsub = self._redis.pubsub()
        self._active_connections: dict[str, set] = {}

    def _channel_key(self, channel: str) -> str:
        return f"ws:channel:{channel}"

    def publish_message(self, channel: str, message: dict) -> bool:
        try:
            payload = json.dumps(message, default=str)
            result = self._redis.publish(self._channel_key(channel), payload)
            logger.debug("Published message to %s, receivers=%s", channel, result)
            return result > 0
        except Exception as exc:
            logger.error("Failed to publish message to %s: %s", channel, exc)
            return False

    def subscribe_to_channel(self, channel: str) -> AsyncGenerator[dict, None]:
        key = self._channel_key(channel)
        self._pubsub.subscribe(key)
        logger.debug("Subscribed to channel %s", channel)
        try:
            while True:
                message = self._pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if message and message.get("type") == "message":
                    try:
                        data = json.loads(message["data"])
                        yield data
                    except json.JSONDecodeError:
                        continue
        except GeneratorExit:
            self._pubsub.unsubscribe(key)
            logger.debug("Unsubscribed from channel %s", channel)

    def broadcast_message(self, channels: list[str], message: dict) -> int:
        count = 0
        for channel in channels:
            if self.publish_message(channel, message):
                count += 1
        logger.debug("Broadcasted to %d/%d channels", count, len(channels))
        return count

    def register_connection(self, channel: str, connection_id: str):
        key = self._channel_key(channel)
        self._redis.sadd(key, connection_id)
        self._active_connections.setdefault(channel, set()).add(connection_id)

    def unregister_connection(self, channel: str, connection_id: str):
        key = self._channel_key(channel)
        self._redis.srem(key, connection_id)
        if channel in self._active_connections:
            self._active_connections[channel].discard(connection_id)

    def get_connection_count(self, channel: str) -> int:
        key = self._channel_key(channel)
        return self._redis.scard(key)

    def close(self):
        try:
            self._pubsub.close()
            self._redis.close()
        except Exception as exc:
            logger.error("Error closing WebSocketScaler: %s", exc)
