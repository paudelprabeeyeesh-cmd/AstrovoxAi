"""Compression support for GZip and Brotli."""

from typing import Optional, Dict, Any
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
import gzip
import brotli
import io


class CompressionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, minimum_size: int = 500):
        super().__init__(app)
        self.minimum_size = minimum_size

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        accept_encoding = request.headers.get("Accept-Encoding", "")
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        if len(body) < self.minimum_size:
            return response
        if "br" in accept_encoding:
            compressed = brotli.compress(body)
            response.headers["Content-Encoding"] = "br"
            response.headers["Content-Length"] = str(len(compressed))
            response.body = compressed
        elif "gzip" in accept_encoding:
            compressed = gzip.compress(body)
            response.headers["Content-Encoding"] = "gzip"
            response.headers["Content-Length"] = str(len(compressed))
            response.body = compressed
        return response


def compress_response(content: bytes, encoding: str = "br") -> tuple[bytes, str]:
    if encoding == "br":
        return brotli.compress(content), "br"
    elif encoding == "gzip":
        return gzip.compress(content), "gzip"
    return content, "identity"
