"""Idempotency dependency wiring for mutating routes.

The store and the contract live in app.idempotency. This is the transport: how a
key arrives, how a conflict and an in-progress attempt are rendered, and how the
replayed/fresh distinction reaches the client's logs.

The header name is the de facto standard, `Idempotency-Key`, because a client
that already sends one should not be asked to learn a second convention.
"""

from __future__ import annotations

from typing import Any, Callable, Optional, Tuple

from fastapi import Header, HTTPException, status

from app.idempotency import (
    IdempotencyConflict,
    IdempotencyInProgress,
    IdempotencyStore,
    replay_or_execute,
)

# Process-level default. A deployment replaces this with a durable store; the
# in-memory one is what the tests and a single-process dev server use.
_default_store: Optional[IdempotencyStore] = None


def get_idempotency_store() -> IdempotencyStore:
    """Return the process-wide idempotency store."""
    global _default_store
    if _default_store is None:
        _default_store = IdempotencyStore()
    return _default_store


def set_idempotency_store(store: IdempotencyStore) -> None:
    """Replace the store, so a deployment installs a durable one at startup."""
    global _default_store
    _default_store = store


IDEMPOTENCY_HEADER = "Idempotency-Key"


def require_idempotency_key(
    idempotency_key: Optional[str] = Header(None, alias=IDEMPOTENCY_HEADER),
) -> str:
    """FastAPI dependency that requires a key on a mutating route.

    Required rather than optional. A key that is optional is a key that is
    usually absent, and a mutating route without one is a route that can be
    double-executed by a network retry.
    """
    if not idempotency_key or not idempotency_key.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"{IDEMPOTENCY_HEADER} is required for this endpoint. A network "
                "retry without one would execute the operation twice."
            ),
        )
    return idempotency_key.strip()


def idempotent_handler(
    operation: Callable[[], Any],
    *,
    key: str,
    caller: str,
    body: bytes,
) -> Tuple[Any, bool]:
    """Run an operation at most once, translating store errors to HTTP.

    The store's three outcomes map onto three different statuses, and the
    mapping is the point: a client that cannot tell a retry from a conflict will
    retry a conflict forever.

      200/201 + replayed=false  fresh execution
      200/201 + replayed=true   the stored result from an earlier attempt
      409                        the same key arrived with a different body
      425                        the first attempt is still running, retry shortly
    """
    store = get_idempotency_store()
    try:
        result, replayed = replay_or_execute(store, key, caller, body, operation)
    except IdempotencyConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
            headers={"Idempotency-Conflicted": "true"},
        ) from exc
    except IdempotencyInProgress as exc:
        raise HTTPException(
            status_code=status.HTTP_425_TOO_EARLY,
            detail=str(exc),
            headers={"Retry-After": str(int(exc.retry_after))},
        ) from exc
    return result, replayed


# The header this module reads, exported so a router declares it in its OpenAPI
# parameters and a client can discover it from the schema rather than from
# documentation that has drifted.
IDEMPOTENCY_KEY_PARAM = {
    "name": IDEMPOTENCY_HEADER,
    "in": "header",
    "required": True,
    "schema": {"type": "string"},
    "description": (
        "Client-generated key making this request retry-safe. The first "
        "execution is stored; a replay with the same key and body returns the "
        "stored result, and a replay with a different body is a 409."
    ),
}
