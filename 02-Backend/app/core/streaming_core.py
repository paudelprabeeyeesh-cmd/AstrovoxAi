"""
Real SSE streaming for chat completions.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional

import asyncio
import json

from fastapi import Request
from sse_starlette import EventSourceResponse

logger = logging.getLogger(__name__)


class StreamEventType(str, Enum):
    MESSAGE_START = "message_start"
    CONTENT_DELTA = "content_delta"
    MESSAGE_STOP = "message_stop"
    TURN_COMPLETE = "turn_complete"
    ERROR = "error"


@dataclass
class StreamEvent:
    event_type: StreamEventType
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)


class StreamingManager:
    """Manages real-time streaming of AI responses."""

    def __init__(self):
        self.active_streams: Dict[str, asyncio.Queue] = {}
        self.stream_subscribers: Dict[str, List[asyncio.Queue]] = defaultdict(list)
        self.typing_indicators: Dict[str, bool] = {}

    async def stream_tokens(self, stream_id: str, token_generator: AsyncGenerator[str, None]) -> AsyncGenerator[StreamEvent, None]:
        """Stream tokens with proper SSE events."""
        yield StreamEvent(event_type=StreamEventType.MESSAGE_START, data={"stream_id": stream_id, "timestamp": time.time()})
        self.typing_indicators[stream_id] = True
        try:
            async for token in token_generator:
                yield StreamEvent(event_type=StreamEventType.CONTENT_DELTA, data={"token": token, "stream_id": stream_id})
        finally:
            self.typing_indicators[stream_id] = False
            yield StreamEvent(event_type=StreamEventType.MESSAGE_STOP, data={"stream_id": stream_id, "timestamp": time.time()})
            yield StreamEvent(event_type=StreamEventType.TURN_COMPLETE, data={"stream_id": stream_id})

    def create_sse_response(self, stream_id: str, token_generator: AsyncGenerator[str, None]) -> EventSourceResponse:
        """Create SSE response for FastAPI."""
        async def event_generator():
            async for event in self.stream_tokens(stream_id, token_generator):
                yield {
                    "event": event.event_type.value,
                    "data": json.dumps(event.data),
                    "timestamp": event.timestamp,
                }

        return EventSourceResponse(event_generator(), media_type="text/event-stream")

    def subscribe_to_stream(self, stream_id: str, queue: asyncio.Queue):
        """Subscribe to an existing stream."""
        self.stream_subscribers[stream_id].append(queue)

    def unsubscribe(self, stream_id: str, queue: asyncio.Queue):
        """Unsubscribe from stream."""
        if queue in self.stream_subscribers[stream_id]:
            self.stream_subscribers[stream_id].remove(queue)

    def is_typing(self, stream_id: str) -> bool:
        """Check if AI is currently generating."""
        return self.typing_indicators.get(stream_id, False)


streaming_manager = StreamingManager()
