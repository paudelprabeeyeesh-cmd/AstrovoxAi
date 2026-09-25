"""SSE streaming for server-sent events."""

from typing import AsyncGenerator, Optional, Dict, Any
import asyncio
import json
from fastapi import Request
from starlette.responses import StreamingResponse


async def event_stream(
    request: Request,
    generator: AsyncGenerator[Dict[str, Any], None],
) -> StreamingResponse:
    async def event_publisher():
        try:
            async for event in generator:
                if await request.is_disconnected():
                    break
                yield f"data: {json.dumps(event)}\n\n"
                await asyncio.sleep(0)
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_publisher(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def simple_stream(data: AsyncGenerator[Dict[str, Any], None]) -> AsyncGenerator[str, None]:
    async for item in data:
        yield f"data: {json.dumps(item)}\n\n"
