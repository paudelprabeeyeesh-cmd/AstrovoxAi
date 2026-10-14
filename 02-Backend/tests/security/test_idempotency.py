"""Tests for idempotency keys.

The contract under test is the one a retrying client depends on: the same key and
body runs once, the same key and a different body is a conflict, and a failed
attempt does not consume the key. A store that fails any of these turns a network
retry into a duplicate charge or a duplicate row.
"""

import os
import sys
import time

os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
sys.path.insert(0, ".")

import pytest

from app.idempotency import (
    IdempotencyConflict,
    IdempotencyInProgress,
    IdempotencyStore,
    body_digest,
    execute_idempotent,
    replay_or_execute,
)


@pytest.fixture
def store():
    return IdempotencyStore(ttl_seconds=900)


BODY = b'{"amount": 100}'


def test_a_replayed_key_returns_the_stored_result(store):
    calls = []

    def op():
        calls.append(1)
        return {"status": "created"}

    first, replayed = execute_idempotent(store, "k1", "u1", BODY, op)
    second, replayed_again = replay_or_execute(store, "k1", "u1", BODY, op)

    assert first == second
    assert replayed is False
    assert replayed_again is True
    # The operation ran once.
    assert len(calls) == 1


def test_the_same_key_with_a_different_body_is_a_conflict(store):
    def op():
        return {"ok": True}

    execute_idempotent(store, "k1", "u1", BODY, op)
    with pytest.raises(IdempotencyConflict):
        execute_idempotent(store, "k1", "u1", b'{"amount": 999}', op)


def test_a_key_is_bound_to_the_caller(store):
    # Two users presenting the same key must not see each other's result. A key
    # scoped to the request rather than the caller is a cache of other people's
    # responses.
    calls = []

    def op():
        calls.append(1)
        return {"n": len(calls)}

    first, _ = execute_idempotent(store, "shared", "u1", BODY, op)
    second, replayed = execute_idempotent(store, "shared", "u2", BODY, op)

    assert replayed is False
    assert first != second, "a different caller was served a cached result"


def test_a_concurrent_retry_is_told_to_wait_rather_than_executing(store):
    # The second attempt must not run concurrently, because the whole point is
    # that the operation happens once.
    store.begin("k1", "u1", body_digest(BODY))

    with pytest.raises(IdempotencyInProgress) as exc:
        execute_idempotent(store, "k1", "u1", BODY, lambda: {"ran": True})

    assert exc.value.retry_after >= 0


def test_a_failed_operation_does_not_consume_the_key(store):
    # A broken first attempt must not wedge the key forever, because then every
    # retry is refused for a reason unrelated to the request.
    def failing():
        raise RuntimeError("provider unavailable")

    with pytest.raises(RuntimeError):
        execute_idempotent(store, "k1", "u1", BODY, failing)

    # The key is reusable, and the store no longer holds it.
    assert store.lookup("k1", "u1") is None or store.lookup("k1", "u1").state != "pending"

    calls = []

    def working():
        calls.append(1)
        return {"ok": True}

    result, replayed = execute_idempotent(store, "k1", "u1", BODY, working)
    assert result == {"ok": True}
    assert replayed is False
    assert len(calls) == 1


def test_a_completed_record_is_returned_after_completion(store):
    store.begin("k1", "u1", body_digest(BODY))
    store.complete("k1", "u1", {"status": "done"}, 201)

    record = store.lookup("k1", "u1")
    assert record is not None
    assert record.state == "complete"
    assert record.result == {"status": "done"}
    assert record.status_code == 201


def test_abandon_drops_a_pending_record(store):
    store.begin("k1", "u1", body_digest(BODY))
    store.abandon("k1", "u1")
    assert store.lookup("k1", "u1") is None


def test_an_expired_record_is_evicted(store):
    # An entry kept forever is both a leak and a way to replay a response long
    # after the underlying state moved on.
    short = IdempotencyStore(ttl_seconds=0)
    short.begin("k1", "u1", body_digest(BODY))
    short.complete("k1", "u1", {"ok": True})
    assert short.lookup("k1", "u1") is None


def test_a_stale_pending_record_expires():
    # A worker may have died mid-flight. Honouring a pending marker forever
    # would permanently wedge that key.
    store = IdempotencyStore(ttl_seconds=0)
    store.begin("k1", "u1", body_digest(BODY))
    # With no TTL the pending marker is already expired, so the key is free to
    # retry rather than being told it is in progress.
    assert store.lookup("k1", "u1") is None
    result, replayed = execute_idempotent(store, "k1", "u1", BODY, lambda: {"ok": True})
    assert result == {"ok": True}
    assert replayed is False


def test_server_issued_keys_are_unique():
    store = IdempotencyStore()
    keys = {store.new_key() for _ in range(1000)}
    assert len(keys) == 1000
    assert all(k.startswith("idem_") for k in keys)


def test_body_digest_is_order_sensitive_but_stable():
    # Digesting exactly what it is given: a caller needing canonical ordering
    # must serialise first. A digest that silently reordered would make two
    # different bodies look like one operation.
    first = body_digest(b'{"a":1,"b":2}')
    second = body_digest(b'{"a":1,"b":2}')
    different = body_digest(b'{"b":2,"a":1}')
    assert first == second
    assert first != different


def test_a_generated_key_still_conflicts_on_a_different_body():
    # A caller that generates its own key still gets conflict detection; there is
    # no path that skips the body comparison.
    store = IdempotencyStore()
    key = store.new_key()
    execute_idempotent(store, key, "u1", BODY, lambda: {"ok": True})
    with pytest.raises(IdempotencyConflict):
        execute_idempotent(store, key, "u1", b"other", lambda: {"ok": True})


def test_the_store_drops_expired_entries_on_size(store):
    # size() evicts, so a long-lived store does not grow without bound.
    store.begin("k1", "u1", body_digest(BODY))
    assert store.size() == 1
    store._records[("u1", "k1")].completed_at = time.time() - 10_000
    assert store.size() == 0


def test_a_replay_of_a_complete_record_does_not_raise_in_progress(store):
    # A client polling for its result must get the result, not another
    # instruction to wait.
    store.begin("k1", "u1", body_digest(BODY))
    store.complete("k1", "u1", {"status": "done"})

    result, replayed = replay_or_execute(store, "k1", "u1", BODY, lambda: {"ran": True})
    assert result == {"status": "done"}
    assert replayed is True


def test_execute_idempotent_raises_on_a_concurrent_retry(store):
    # execute_idempotent is the first-attempt path and is strict; the client is
    # told to wait rather than served a partial state.
    store.begin("k1", "u1", body_digest(BODY))
    with pytest.raises(IdempotencyInProgress):
        execute_idempotent(store, "k1", "u1", BODY, lambda: {"ran": True})


def test_abandoning_a_completed_record_keeps_it(store):
    # Only a pending record is abandoned. A completed result is durable and
    # must survive a later failure on the same key.
    store.begin("k1", "u1", body_digest(BODY))
    store.complete("k1", "u1", {"status": "done"})
    store.abandon("k1", "u1")
    assert store.lookup("k1", "u1").state == "complete"


def test_completing_an_unknown_key_raises(store):
    with pytest.raises(KeyError):
        store.complete("nope", "u1", {"ok": True})
