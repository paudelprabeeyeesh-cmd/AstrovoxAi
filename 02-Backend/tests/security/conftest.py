"""Shared fixtures for the security suite."""

import pytest


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Give the rate limiter fresh state before each test.

    The limiter is a process-global with in-memory sliding windows keyed by
    client identity. Suites that make many requests (the integration lifecycle
    suite does) fill the anonymous bucket, so a later test on ``/health``
    gets a 429 for a reason unrelated to the behaviour under test — the result
    then depends on collection order instead of on the code.

    The global is *replaced*, not merely cleared: several internal maps and
    caches hold window state, and clearing only one of them leaves the rest
    pointing at the same exhausted windows.
    """
    import app.middleware.security.rate_limit_hardened as rl

    previous = rl._GLOBAL_LIMITER
    rl._GLOBAL_LIMITER = rl.RateLimiter()
    try:
        yield
    finally:
        rl._GLOBAL_LIMITER = previous
