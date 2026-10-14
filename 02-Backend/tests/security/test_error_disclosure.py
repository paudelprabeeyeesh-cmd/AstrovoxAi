"""Regression tests for internal-error disclosure.

Route handlers interpolate `str(exc)` into `HTTPException(detail=...)` on 5xx,
which puts database paths, SQL fragments and exception class names in the
response body. The client must get a generic message instead, with the real
cause kept in the log under the same correlation id.
"""

from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from app.middleware.error_handler import (
    GENERIC_SERVER_ERROR,
    _looks_like_raw_exception,
    http_exception_handler,
    unhandled_exception_handler,
)


class _Request:
    def __init__(self, correlation_id="corr-1"):
        self.method = "POST"
        self.url = type("U", (), {"path": "/api/things"})()
        self.state = type("S", (), {"correlation_id": correlation_id})()


def _body(response: JSONResponse) -> str:
    return response.body.decode()


def test_raw_exception_details_are_detected():
    assert _looks_like_raw_exception("no such table: users")
    assert _looks_like_raw_exception(
        "sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such table"
    )
    assert _looks_like_raw_exception(
        "ValueError('cannot connect to /var/lib/db.sqlite')"
    )


def test_human_written_details_are_not_stripped():
    assert not _looks_like_raw_exception("Quota exceeded for this workspace")
    assert not _looks_like_raw_exception("Invalid model name")


async def test_500_with_str_exc_returns_generic_message():
    response = await http_exception_handler(
        _Request(), StarletteHTTPException(status_code=500, detail="no such table: users")
    )
    assert response.status_code == 500
    body = _body(response)
    assert GENERIC_SERVER_ERROR[:40] in body
    assert "no such table" not in body


async def test_500_with_sqlalchemy_error_is_generic():
    leak = "sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such table: users"
    response = await http_exception_handler(
        _Request(), StarletteHTTPException(status_code=500, detail=leak)
    )
    assert response.status_code == 500
    body = _body(response)
    for fragment in ("sqlalchemy", "sqlite3", "no such table"):
        assert fragment not in body


async def test_500_keeps_a_human_message():
    response = await http_exception_handler(
        _Request(), StarletteHTTPException(status_code=500, detail="Upstream timeout")
    )
    assert response.status_code == 500
    assert "Upstream timeout" in _body(response)


async def test_4xx_detail_is_not_sanitised():
    """A 400 names the caller's own mistake, which must stay visible."""
    response = await http_exception_handler(
        _Request(), StarletteHTTPException(status_code=400, detail="Missing model")
    )
    assert response.status_code == 400
    assert "Missing model" in _body(response)


async def test_unhandled_exception_is_generic():
    response = await unhandled_exception_handler(_Request(), RuntimeError("db path /var/lib/x.sqlite"))
    assert response.status_code == 500
    body = _body(response)
    assert GENERIC_SERVER_ERROR[:40] in body
    assert "/var/lib/x.sqlite" not in body


async def test_correlation_id_is_preserved_for_support():
    response = await http_exception_handler(
        _Request("corr-abc"),
        StarletteHTTPException(status_code=500, detail="no such table: users"),
    )
    assert response.headers.get("X-Correlation-ID") == "corr-abc"
    assert "corr-abc" in _body(response)
