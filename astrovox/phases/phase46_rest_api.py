"""REST API server for the Astrovox platform."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable


@dataclass
class Route:
    """A REST route definition."""
    path: str
    methods: list[str]
    handler: Callable
    prefix: str = ""

    @property
    def full_path(self) -> str:
        return self.prefix + self.path


@dataclass
class APIResponse:
    """A REST API response."""
    status: int
    body: dict | list | str | None = None
    headers: dict = field(default_factory=dict)

    def to_tuple(self) -> tuple:
        if self.body is None:
            return (self.status, self.headers, b"")
        data = self.body
        if isinstance(data, str):
            body = data.encode("utf-8")
        else:
            body = json.dumps(data).encode("utf-8")
        self.headers.setdefault("Content-Type", "application/json")
        return (self.status, self.headers, body)


class RESTServer:
    """Simple REST API server."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8080, prefix: str = "/api"):
        self.host = host
        self.port = port
        self.prefix = prefix
        self.routes: list[Route] = []
        self.middlewares: list[Callable] = []

    def route(self, path: str, methods: list[str] | str = None, **options):
        """Decorator to register a route."""
        def decorator(handler: Callable) -> Callable:
            methods = methods or options.pop("methods", ["GET"])
            if isinstance(methods, str):
                methods = [methods]
            self.routes.append(Route(path=path, methods=[m.upper() for m in methods],
                                     handler=handler, prefix=self.prefix))
            return handler
        return decorator

    def use(self, middleware: Callable) -> None:
        self.middlewares.append(middleware)

    def handle_request(self, method: str, path: str, body: bytes = b"",
                       headers: dict | None = None) -> APIResponse:
        """Route an incoming request."""
        path = path.split("?")[0]
        for route in self.routes:
            pattern = re.sub(r"<([^>]+)>", r"(?P<\1>[^/]+)", route.path)
            m = re.match(f"^{pattern}$", path)
            if m and method in route.methods:
                req = APIRequest(method=method, path=path, body=body,
                                 params=dict(m.groupdict()), headers=headers or {})
                for mw in self.middlewares:
                    req = mw(req) or req
                resp = route.handler(req)
                if isinstance(resp, APIResponse):
                    return resp
                return APIResponse(status=200, body=resp)
        return APIResponse(status=404, body={"error": "not found"})

    def start(self, blocking: bool = True) -> None:
        """Start the server."""
        server = HTTPServer((self.host, self.port), _Handler(self))
        print(f"REST server listening on http://{self.host}:{self.port}{self.prefix}")
        if blocking:
            server.serve_forever()


class APIRequest:
    """An API request."""

    def __init__(self, method: str, path: str, body: bytes, params: dict,
                 headers: dict | None = None):
        self.method = method
        self.path = path
        self.params = params
        self.headers = headers or {}
        self._body_cache: Any = None
        self.body = body

    @property
    def data(self) -> dict:
        if self._body_cache is None and self.body:
            try:
                self._body_cache = json.loads(self.body.decode("utf-8"))
            except Exception:
                self._body_cache = {}
        return self._body_cache or {}


class _Handler(BaseHTTPRequestHandler):
    def __init__(self, api: RESTServer, *args, **kwargs):
        self._api = api
        super().__init__(*args, **kwargs)

    def log_message(self, format, *args):
        pass

    def _send(self, status: int, headers: dict, body: bytes) -> None:
        self.send_response(status)
        for k, v in headers.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        resp = self._api.handle_request("GET", self.path, headers=self.headers)
        self._send(*resp.to_tuple())

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        resp = self._api.handle_request("POST", self.path, body=body, headers=self.headers)
        self._send(*resp.to_tuple())

    def do_PUT(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        resp = self._api.handle_request("PUT", self.path, body=body, headers=self.headers)
        self._send(*resp.to_tuple())

    def do_DELETE(self):
        resp = self._api.handle_request("DELETE", self.path, headers=self.headers)
        self._send(*resp.to_tuple())
