# ADR-0008: HTTPS redirect uses 307/308, never 301/302

- Status: accepted
- Date: 2026-10-10
- Tasks: D05-09, D12-01 (adjacent)

## Context

`HTTPSRedirectMiddleware` redirected plain-HTTP requests with
`301` (or `302` when `permanent=False`). A 301/302 authorises the client to
rewrite the method to GET when following the redirect. Consequence: every
`POST /auth/signup` became `GET /auth/signup` after the redirect, and the router
answered `405 Method Not Allowed`. The client cannot tell "use HTTPS" from "this
route does not accept POST".

This also hid a second problem: tests could not follow the redirect at all,
because the test transport speaks plain HTTP.

## Decision

Use the method-preserving redirect codes: `308` for the permanent case and `307`
otherwise. `HTTPS_REDIRECT_ENABLED=0` remains the switch to disable enforcement
outright, which is what the test environment sets.

## Consequences

- A plain-HTTP write retried against TLS keeps its method and body, so it reaches
  the intended handler instead of a 405.
- Clients that do not follow 307/308 will drop the request; those clients were
  already broken, and now they fail loudly instead of silently.
- Disabling enforcement is now an explicit, documented environment switch rather
  than a side effect of the redirect being unfollowable.

## Alternatives considered

- Keep 301 and special-case POST. Rejected: per-route redirect semantics is more
  machinery than the problem needs.
- Disable the middleware entirely. Rejected: TLS enforcement is a required
  control (D05-09); only the code needed fixing.