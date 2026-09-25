"""Content negotiation helpers for format-aware responses."""

from __future__ import annotations

from typing import Any, Dict, Optional


ACCEPTED_FORMATS = {
    "application/json": "json",
    "application/xml": "xml",
    "text/html": "html",
    "text/plain": "text",
    "*/*": "json",
}


def negotiate_format(accept_header: Optional[str], default: str = "json") -> str:
    if not accept_header:
        return default
    for media in accept_header.split(","):
        media = media.strip().split(";")[0].strip()
        fmt = ACCEPTED_FORMATS.get(media)
        if fmt:
            return fmt
    return default


def format_response(data: Any, fmt: str) -> Any:
    if fmt == "json":
        return data
    if fmt == "text":
        return str(data)
    if fmt == "xml":
        return _to_xml(data)
    if fmt == "html":
        return f"<pre>{data!r}</pre>"
    return data


def _to_xml(data: Any) -> str:
    if isinstance(data, dict):
        parts = []
        for key, value in data.items():
            parts.append(f"<{key}>{_to_xml(value)}</{key}>")
        return "".join(parts)
    if isinstance(data, list):
        return "".join(_to_xml(item) for item in data)
    from html import escape
    return escape(str(data))
