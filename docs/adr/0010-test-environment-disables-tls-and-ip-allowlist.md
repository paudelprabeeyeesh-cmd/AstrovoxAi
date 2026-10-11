# ADR-0010: Test environment disables TLS and IP enforcement

- Status: accepted
- Date: 2026-10-10
- Tasks: D17-02, D17-04

## Context

Two middleware make the test transport unusable as shipped:
- `HTTPSRedirectMiddleware` rejects the plain-HTTP transport (see ADR-0008).
- `IPEnforcementMiddleware` reads `request.client.host`. Starlette's test
  transport reports the literal host `testclient`, and `ip_filter.check()`
  correctly rejects it as `invalid_ip`, so every request became a 403 before
  routing.

A third control, `CSRFMiddleware`, needs an `X-CSRF-Token` header matching the
`csrftoken` cookie on state-changing requests.

## Decision

Keep all three controls enabled and make the **test client** conform rather than
disabling anything but the transport-level concerns:
- `HTTPS_REDIRECT_ENABLED=0` and `ASTROVOX_TEST_MODE=1` in
  `tests/conftest.py`, because the test transport cannot do TLS.
- Test clients construct with `client=("127.0.0.1", 50000)` so the IP allowlist
  sees a valid loopback address.
- Fixtures set the CSRF header and cookie together.

## Consequences

- CSRF and IP allowlist behaviour is still exercised, not bypassed: the test
  client satisfies them, and a request without the token still 403s.
- Only TLS enforcement is disabled in tests, and it is documented as an
  environment switch with a stated reason.
- Import time is slow (~27s) because importing `app.main` attempts a real
  Supabase connection against a refused local port. That is an environment
  artifact, recorded in `docs/BASELINE.md`, and it is the cause of the one
  remaining auth-flow failure.

## Alternatives considered

- Patch out the middleware in fixtures. Rejected: hides real regressions in the
  controls that are the whole point of D17-02/D17-04.
- Make the IP filter fail-open for unparseable hosts. Rejected: a production
  request with an unparseable peer address should be refused, not allowed