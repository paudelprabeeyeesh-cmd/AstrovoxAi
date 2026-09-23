"""Cross-cutting HTTP security and observability controls for the Astrovox API."""

import re
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class SecurityHeadersMiddleware:
    """Attach baseline browser-facing security headers to every HTTP response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_security_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.setdefault("X-Content-Type-Options", "nosniff")
                headers.setdefault("X-Frame-Options", "DENY")
                headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
                headers.setdefault(
                    "Permissions-Policy", "camera=(), geolocation=(), microphone=()"
                )
                headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
            await send(message)

        await self.app(scope, receive, send_with_security_headers)


class RequestIDMiddleware:
    """Attach a correlation id to every HTTP response.

    A caller-provided id is accepted only when it is a short, safe token. This
    lets frontend and gateway logs correlate a request without allowing
    arbitrary header values to be reflected into responses.
    """

    _SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = dict(scope.get("headers", [])).get(b"x-request-id", b"").decode(
            "ascii", errors="ignore"
        )
        request_id = incoming if self._SAFE_REQUEST_ID.fullmatch(incoming) else str(uuid4())

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.setdefault("X-Request-ID", request_id)
            await send(message)

        await self.app(scope, receive, send_with_request_id)
