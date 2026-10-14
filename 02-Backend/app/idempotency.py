"""Idempotency keys for mutating requests.

A client that retries a POST because it never saw the response must not cause
the operation to run twice. Without a key, a network retry creates a second row,
a second charge, a second message - and the caller has no way to tell which of
the two responses it already acted on.

The contract is the standard one:

  - the first request with an unseen key executes and its result is stored
  - a replay of the SAME key and body returns the stored result unchanged
  - a replay of the same key with a DIFFERENT body is a conflict, not a retry,
    because honouring it would mean the client's intent is ambiguous

A key is bound to the caller, not just to the request. Two users presenting the
same key must not see each other's results, which is the difference between an
idempotency table and a cache of other people's responses.

Results expire. An entry kept forever is both a leak and a way to replay a
response long after the underlying state has changed.
"""

from __future__ import annotations

import hashlib
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Tuple


class IdempotencyConflict(Exception):
    """The same key was presented with a different body."""

    def __init__(self, key: str) -> None:
        super().__init__(
            f"idempotency key {key!r} was already used with a different body"
        )
        self.key = key


class IdempotencyInProgress(Exception):
    """The same key is still executing.

    Raised rather than blocking. A caller that retries while the first request
    is running must not silently wait on a lock it does not own, and must not
    execute concurrently - so the second attempt is told to retry shortly.
    """

    def __init__(self, key: str, retry_after: float = 1.0) -> None:
        super().__init__(f"idempotency key {key!r} is in progress")
        self.key = key
        self.retry_after = retry_after


@dataclass
class IdempotencyRecord:
    """A stored outcome, or a marker that work is underway."""

    key: str
    body_digest: str
    state: str  # "pending" or "complete"
    result: Any = None
    status_code: int = 0
    created_at: float = 0.0
    completed_at: Optional[float] = None
    # The caller this record belongs to. Present so a key is scoped to the
    # identity that owns it rather than to the process.
    caller: str = ""

    def is_expired(self, ttl_seconds: float, now: Optional[float] = None) -> bool:
        if self.completed_at is None:
            # A pending record that never completed is expired by age alone:
            # the worker may have died mid-flight, and honouring a marker
            # forever would permanently wedge that key.
            reference = self.created_at
        else:
            reference = self.completed_at
        if now is None:
            now = time.time()
        return (now - reference) > ttl_seconds


def body_digest(body_bytes: bytes) -> str:
    """Digest the request body, so key+body identifies an operation.

    The canonical form matters: two clients sending the same semantic request
    with keys in a different order must not look like two different operations.
    A caller that needs that should serialise to a canonical form before
    hashing; this digests exactly what it is given and does not guess.
    """
    return hashlib.sha256(body_bytes).hexdigest()


@dataclass
class IdempotencyStore:
    """In-memory idempotency store.

    In-memory because the rest of this module is dependency-free, and because the
    semantics under test - what happens on a replay, a conflict, a concurrent
    retry, and an expiry - do not depend on the backing. A production deployment
    substitutes a durable store that keeps these properties.
    """

    ttl_seconds: float = 900.0
    _records: Dict[Tuple[str, str], IdempotencyRecord] = field(default_factory=dict)
    _lock: Any = None

    def __post_init__(self) -> None:
        # threading is imported here so this module stays importable in
        # environments that do not want threads for anything else.
        import threading

        self._lock = threading.RLock()

    # -- keys ---------------------------------------------------------------

    @staticmethod
    def new_key() -> str:
        """A fresh key for a client that does not supply one.

        Supplied by the store rather than by the client because a server-issued
        key is the safe default for a caller that cannot generate one, and a
        caller that supplies its own keeps the conflict detection either way.
        """
        return "idem_" + secrets.token_hex(16)

    # -- operations ---------------------------------------------------------

    def begin(self, key: str, caller: str, digest: str) -> IdempotencyRecord:
        """Claim a key, or explain why it cannot be claimed.

        Returns the record so a caller can store state on it, or raises:
        IdempotencyConflict for a different body, IdempotencyInProgress for a
        concurrent attempt.
        """
        with self._lock:
            self._evict_expired_locked()
            composite = (caller, key)
            existing = self._records.get(composite)

            if existing is not None:
                if existing.body_digest != digest:
                    raise IdempotencyConflict(key)
                if existing.state == "pending":
                    raise IdempotencyInProgress(key)
                return existing

            record = IdempotencyRecord(
                key=key,
                body_digest=digest,
                state="pending",
                created_at=time.time(),
                caller=caller,
            )
            self._records[composite] = record
            return record

    def complete(
        self,
        key: str,
        caller: str,
        result: Any,
        status_code: int = 200,
    ) -> IdempotencyRecord:
        """Store the outcome of a completed operation."""
        with self._lock:
            record = self._records.get((caller, key))
            if record is None:
                raise KeyError(f"no pending record for key {key!r}")
            record.state = "complete"
            record.result = result
            record.status_code = status_code
            record.completed_at = time.time()
            return record

    def abandon(self, key: str, caller: str) -> None:
        """Drop a pending record so the key can be retried.

        Called when the operation failed. Without it a failed first attempt
        wedges the key forever: every later retry is told the key is in
        progress, which is true, and never stops being true.
        """
        with self._lock:
            composite = (caller, key)
            record = self._records.get(composite)
            if record is not None and record.state == "pending":
                del self._records[composite]

    def lookup(self, key: str, caller: str) -> Optional[IdempotencyRecord]:
        """Return a stored record, honouring expiration."""
        with self._lock:
            self._evict_expired_locked()
            return self._records.get((caller, key))

    # -- internals ----------------------------------------------------------

    def _evict_expired_locked(self) -> None:
        now = time.time()
        expired = [
            composite
            for composite, record in self._records.items()
            if record.is_expired(self.ttl_seconds, now)
        ]
        for composite in expired:
            del self._records[composite]

    def size(self) -> int:
        with self._lock:
            self._evict_expired_locked()
            return len(self._records)


def execute_idempotent(
    store: IdempotencyStore,
    key: str,
    caller: str,
    body_bytes: bytes,
    operation: Callable[[], Any],
) -> Tuple[Any, bool]:
    """Run an operation exactly once per (caller, key, body).

    Returns (result, replayed). `replayed` is True when the response came from
    a previous execution, so a caller can tell a fresh outcome from a stored
    one - a distinction a client needs in order to log "retried" rather than
    "executed twice".

    A failing operation does not consume the key. Raising leaves the pending
    record abandoned so the client can retry, because holding a key after a
    failure means the next attempt is refused for a reason that has nothing to
    do with it.
    """
    digest = body_digest(body_bytes)
    store.begin(key, caller, digest)
    try:
        result = operation()
    except Exception:
        store.abandon(key, caller)
        raise
    store.complete(key, caller, result)
    return result, False


def replay_or_execute(
    store: IdempotencyStore,
    key: str,
    caller: str,
    body_bytes: bytes,
    operation: Callable[[], Any],
) -> Tuple[Any, bool]:
    """Return a stored outcome when one exists, otherwise execute.

    The counterpart to execute_idempotent, for the retry path: it does not raise
    IdempotencyInProgress, because on a replay the client is expected to be
    polling and needs the stored result rather than another instruction to
    wait.
    """
    digest = body_digest(body_bytes)
    record = store.lookup(key, caller)
    if record is not None and record.state == "complete" and record.body_digest == digest:
        return record.result, True

    store.begin(key, caller, digest)
    try:
        result = operation()
    except Exception:
        store.abandon(key, caller)
        raise
    store.complete(key, caller, result)
    return result, False
