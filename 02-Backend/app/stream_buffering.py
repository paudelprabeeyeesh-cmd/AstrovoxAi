"""Stream buffering helper for batching and chunked I/O."""

import logging
from typing import AsyncIterator, List

logger = logging.getLogger("astrovox.stream")


class StreamBuffer:
    """Buffer async stream items into batches."""

    def __init__(self, buffer_size: int = 1024 * 1024, batch_size: int = 10):
        self._buffer_size = buffer_size
        self._batch_size = batch_size
        self._buffer: List[bytes] = []
        self._buffer_len = 0

    async def buffer_stream(self, stream: AsyncIterator[bytes]) -> AsyncIterator[bytes]:
        """Buffer a byte stream and yield complete chunks."""
        async for chunk in stream:
            self._buffer.append(chunk)
            self._buffer_len += len(chunk)
            if self._buffer_len >= self._buffer_size or len(self._buffer) >= self._batch_size:
                yield b"".join(self._buffer)
                self._buffer.clear()
                self._buffer_len = 0
        if self._buffer:
            yield b"".join(self._buffer)

    async def buffer_lines(self, stream: AsyncIterator[bytes], delimiter: bytes = b"\n") -> AsyncIterator[str]:
        """Buffer a byte stream and yield complete lines."""
        remainder = b""
        async for chunk in stream:
            data = remainder + chunk
            lines = data.split(delimiter)
            remainder = lines.pop()
            for line in lines:
                yield line.decode("utf-8", errors="replace")
        if remainder:
            yield remainder.decode("utf-8", errors="replace")

    def reset(self) -> None:
        self._buffer.clear()
        self._buffer_len = 0
