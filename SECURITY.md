# Security Policy

## Supported Versions

Only the latest commit on `main` receives security fixes. There is no
long-term support branch yet; if you need one, open an issue.

This project is pre-release and under active development. Treat every
deployment as untested production infrastructure until it has passed its
own load and restore tests.

## Reporting a Vulnerability

Report privately through GitHub Security Advisories:
`https://github.com/AstrovoxAi/AstrovoxAi/security/advisories/new`

Include the affected endpoint or file, the impact, and reproduction steps.
Do not open a public issue for an unreported vulnerability.

Expected response:

| Stage | Target |
|---|---|
| Acknowledgement | 3 business days |
| Triage and severity | 7 business days |
| Fix or mitigation plan | 30 days for high severity |
| Public disclosure | After a fix ships, or 90 days, whichever is first |

## Severity We Care About Most

1. Cross-tenant data exposure (one account reading another's data).
2. Credential or key exposure, especially anything that would appear in a
   browser bundle.
3. Account takeover: session forgery, token leak, missing verification.
4. Prompt injection that reaches a tool with side effects.
5. Sandbox escape.
6. Denial of service through an unbounded or unpriced path, including AI
   spend.

Items 1 through 3 are the ones that cannot be fixed after the fact without
forcing users to rotate.

## Current Controls

| Control | Location | Test |
|---|---|---|
| Provider token verification with allowlist | `02-Backend/app/auth/__init__.py` | `tests/security/test_token_leaks.py` |
| Single-use tokens delivered by email only | `02-Backend/app/services/token_mailer.py` | same |
| Explicit-memory policy (deny list + instruction override) | `internal/memory/policy.py` | `internal/memory/policy_test.py` |
| Prompt injection corpus | `app/security/`, `app/safety/` | `02-Backend/tests/security/test_prompt_injection.py` |
| Brute-force lockout, rotation, revocation | `02-Backend/app/security/` | `02-Backend/tests/security/` |
| Router load failure is loud, not silent | `02-Backend/app/router_loader.py` | `tests/security/test_token_leaks.py` |
| Stripe webhook customer mapping verification | `02-Backend/app/billing.py` | `tests/security/test_security_regression.py` |
| Non-root containers, tini as PID 1, wheels-only runtime | `Dockerfile.backend`, `Dockerfile.frontend` | `compose-smoke` CI job |
| CSP without `unsafe-inline`, no fake nonce, headers on every location | `nginx/snippets/security-headers.conf` | `frontend-secret-audit` CI job |
| Real coverage gate | `.github/workflows/security.yml` | `coverage-enforcement` CI job |

## Known Gaps

Stated plainly, because a security document that only lists wins is not
trustworthy.

- **No rate limiter backing store.** The limiter is in-process and
  unbounded; it is keyed on a client IP that a reverse proxy can collapse
  to a single bucket. Not yet fixed.
- **No server-side AI spend cap.** A single account can burn provider
  spend within its rate limit. Not yet fixed.
- **Regex-based injection detection.** Lexical, not semantic. A phrasing
  that matches no known pattern passes.
- **No SAST on application code.** Trivy and gitleaks run; CodeQL does not.
- **Plugin code runs in-process.** A malicious plugin can read the
  provider credentials from the environment. Plugin execution needs to be
  a separate process before third-party plugins are enabled.
- **`.env` was tracked in git.** It has been removed from the index and is
  now covered by `.gitignore`; see the rotation checklist in
  `docs/SECRET_ROTATION.md`.

## Secret Handling

- Never commit a secret. `.env` is ignored and untracked.
- Never place a privileged key in a `VITE_` variable. Vite inlines every
  `VITE_` variable into the browser bundle, so it is published to every
  visitor. Frontend code may use only the anonymous key, project id,
  publishable key, API URL, and the VAPID public key.
- CI runs gitleaks and trufflehog over the full history and rejects
  privileged patterns in `src/`.
- A secret that has reached git history is compromised, even if the commit
  is later removed. Rotate it; deleting the commit is not remediation.
