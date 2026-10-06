"""Streaming responses for Astrovox."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Iterator


@dataclass
class StreamChunk:
    """A chunk of streamed output."""
    token: str = ""
    finish_reason: str | None = None
    metadata: dict = field(default_factory=dict)

    def to_json(self) -> str:
        return f'{{"token": {repr(self.token)}, "finish_reason": {repr(self.finish_reason)}}}'


class StreamGenerator:
    """Generate streaming responses."""

    def __init__(self, max_tokens: int = 256):
        self.max_tokens = max_tokens

    def stream(self, text: str) -> Iterator[StreamChunk]:
        words = text.split()
        for i, word in enumerate(words):
            if i >= self.max_tokens:
                yield StreamChunk(token="", finish_reason="length")
                return
            yield StreamChunk(token=word + " ")
        yield StreamChunk(token="", finish_reason="stop")

    def stream_async(self, text: str) -> AsyncIterator[StreamChunk]:
        for chunk in self.stream(text):
            yield chunk

    def count_tokens(self, text: str) -> int:
        return len(text.split())
