# ADR-0007: PII redaction excludes auth and identity endpoints

- Status: accepted
- Date: 2026-10-10
- Task: D17-04, D08-11

## Context

`PIIRedactionMiddleware` masks email-shaped substrings in JSON responses. It was
applied to every route, so `POST /auth/signup` returned `n***@***.***` instead of
the address the caller had just submitted. The signup contract — and every test
that asserts the created user's email — expects the address echoed back.

Two separate defects made this worse than it needed to be:
1. `exclude_paths` was matched exactly, so the documented exclusion `/auth` did
   not cover `/auth/signup`.
2. The middleware read `response.url`, which does not exist on
   `_StreamingResponse`, so any streaming endpoint raised `AttributeError`
   inside the middleware and produced a 500.

## Decision

Redact by default, with explicit exclusions:
- Auth surfaces (`/auth*`) echo the caller's own identity back to that caller and
  are excluded.
- Profile surfaces (`/users/me`, `/account/profile`) are excluded for the same
  reason.
- Exclusion matches by **prefix**, so a family of routes is one entry.
- Streaming responses are skipped entirely — rewriting a stream would require
  buffering the body, which defeats streaming — and the attribute is only
  touched on responses that actually have `url`.

## Consequences

- Signup/login/logout responses keep the email the caller sent, which is what a
  client needs to confirm an account.
- Everything else still gets masked, so the control is not weakened elsewhere.
- If a future endpoint returns a third party's email it must be added to the
  redaction set deliberately, not by accident of falling outside a prefix.

## Alternatives considered

- Drop response redaction. Rejected: it is a real control for endpoints that
  echo stored data of other users (admin listings, exports).
- Mask only on non-2xx responses. Rejected: leaks are just as likely on 200s.