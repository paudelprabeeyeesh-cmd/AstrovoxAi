import asyncio
import json
import logging
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional

logger = logging.getLogger(__name__)


@dataclass
class SSEEvent:
    event: str
    data: Any
    event_id: Optional[str] = None
    retry: Optional[int] = None

    def encode(self) -> str:
        lines = []
        if self.event_id is not None:
            lines.append(f"id: {self.event_id}")
        if self.event is not None:
            lines.append(f"event: {self.event}")
        if self.retry is not None:
            lines.append(f"retry: {self.retry}")
        payload = (
            json.dumps(self.data, default=str)
            if not isinstance(self.data, str)
            else self.data
        )
        for line in payload.splitlines():
            lines.append(f"data: {line}")
        lines.append("")
        return "\n".join(lines)


def generate_event_id() -> str:
    return secrets.token_urlsafe(16)


def format_sse(event: str, data: Any, event_id: Optional[str] = None, retry: Optional[int] = None) -> str:
    return SSEEvent(event=event, data=data, event_id=event_id, retry=retry).encode()


@dataclass
class StreamState:
    event_id: str
    provider: str
    model: str
    started_at: float = field(default_factory=time.time)
    tokens_yielded: int = 0
    fallback_count: int = 0
    completed: bool = False
    error: Optional[str] = None


class KeepAliveGenerator:
    def __init__(self, interval_seconds: int = 15, event_id: Optional[str] = None):
        self.interval_seconds = interval_seconds
        self.event_id = event_id

    async def generate(self, inner: AsyncIterator[str]) -> AsyncIterator[str]:
        last_yield = time.monotonic()
        buffer = ""
        try:
            while True:
                now = time.monotonic()
                if now - last_yield >= self.interval_seconds:
                    yield ": keep-alive\n\n"
                    last_yield = now
                try:
                    chunk = await asyncio.wait_for(inner.__anext__(), timeout=0.5)
                    buffer += chunk
                    if "\n\n" in buffer:
                        parts = buffer.split("\n\n")
                        for part in parts[:-1]:
                            yield part + "\n\n"
                        buffer = parts[-1]
                    last_yield = time.monotonic()
                except asyncio.TimeoutError:
                    continue
                except StopAsyncIteration:
                    if buffer:
                        yield buffer
                    break
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.error("KeepAliveGenerator error: %s", exc)
            yield format_sse("error", {"message": "Stream interrupted", "detail": str(exc)})


class StreamFallbackChain:
    def __init__(self, primary_provider, fallback_providers: list, max_fallbacks: int = 2):
        self.primary_provider = primary_provider
        self.fallback_providers = fallback_providers
        self.max_fallbacks = max_fallbacks
        self.fallback_count = 0
        self.last_fallback_reason: Optional[str] = None

    def next_provider(self, reason: Optional[str] = None) -> Optional[Any]:
        if self.fallback_count < self.max_fallbacks and self.fallback_providers:
            provider = self.fallback_providers[self.fallback_count]
            self.fallback_count += 1
            self.last_fallback_reason = reason
            logger.warning(
                "Falling back to provider %s (attempt %d/%d). Reason: %s",
                provider.name,
                self.fallback_count,
                self.max_fallbacks,
                reason,
            )
            return provider
        return None

    def reset(self):
        self.fallback_count = 0
        self.last_fallback_reason = None
