"""WebSocket API for real-time streaming."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine


@dataclass
class WSMessage:
    """A WebSocket message."""
    event: str
    payload: Any = None
    sid: str = ""

    def to_json(self) -> str:
        return json.dumps({"event": self.event, "payload": self.payload, "sid": self.sid})

    @classmethod
    def from_json(cls, data: str) -> "WSMessage":
        d = json.loads(data)
        return cls(event=d.get("event", "message"), payload=d.get("payload"), sid=d.get("sid", ""))


class WSHandler:
    """WebSocket handler for a single connection."""

    def __init__(self, ws, sid: str):
        self.ws = ws
        self.sid = sid
        self.handlers: dict[str, Callable[[WSMessage], Any]] = {}
        self._running = False

    def on(self, event: str, handler: Callable[[WSMessage], Any]) -> None:
        self.handlers[event] = handler

    async def run(self) -> None:
        self._running = True
        try:
            async for msg in self.ws:
                wm = WSMessage.from_json(msg)
                h = self.handlers.get(wm.event)
                if h:
                    result = h(wm)
                    if asyncio.iscoroutine(result):
                        await result
        except Exception:
            pass
        finally:
            self._running = False

    async def send(self, event: str, payload: Any = None) -> None:
        await self.ws.send_text(json.dumps({"event": event, "payload": payload, "sid": self.sid}))

    async def close(self) -> None:
        if self.sid:
            await self.ws.close()


class WebSocketServer:
    """WebSocket streaming server."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8081):
        self.host = host
        self.port = port
        self.sessions: dict[str, WSHandler] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    def register(self, sid: str, handler: Callable[[WSMessage], Any], event: str = "message") -> None:
        async def wrap(wm: WSMessage) -> None:
            if wm.sid == sid:
                await handler(wm)
        # registration deferred to connect time
        self.sessions[sid] = None

    async def start(self) -> None:
        from aiohttp import web
        app = web.Application()
        app.router.add_get("/ws", self._websocket_handler)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        print(f"WebSocket server listening on ws://{self.host}:{self.port}/ws")

    async def _websocket_handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        handler = WSHandler(ws, sid=str(len(self.sessions) + 1))
        sid = handler.sid
        self.sessions[sid] = handler
        try:
            await handler.run()
        finally:
            self.sessions.pop(sid, None)
        return ws
