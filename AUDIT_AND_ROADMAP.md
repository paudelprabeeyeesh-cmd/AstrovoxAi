# AstrovoxAI — Audit & Roadmap

**Generated:** 2026-09-14  
**Status:** ACTIVE — Tier 1 Execution Underway

## Executive Summary

AstrovoxAI is a functional prototype with a working LLM routing core, auth primitives, and Stripe billing hooks. It is not production-ready. Critical security holes, architectural anti-patterns, missing observability, and no enterprise compliance posture block scaling. This document decomposes every deficiency into a prioritized, tiered execution plan with granular tickets, file-specific implementation steps, and verification methods.

## Gap Deconstruction

| ID | Category | Gap | Severity | Location |
|---|----------|-----|----------|----------|
| S-01 | Security | Debug exception handler exposes stack traces in production | CRITICAL | app/main.py:123-132 |
| S-02 | Security | Email verification bypassed on registration (email_verified=1) | CRITICAL | app/auth.py:59 |
| S-03 | Security | No WebSocket authentication on /ws/chat or /ws/voice | CRITICAL | app/main.py:652-737 |
| S-04 | Security | Stripe webhook handler does not verify customer mapping | HIGH | app/billing.py:81-94 |
| S-05 | Security | Rate-limit middleware re-parses JWT on every request | HIGH | app/rate_limit.py:16-26 |
| S-06 | Security | CORS origins hardcoded to localhost + astrovox.ai only | HIGH | app/main.py:87-93 |
| S-07 | Security | No CSRF protection on state-changing endpoints | HIGH | Global |
| S-08 | Security | No request timeout / max payload size enforcement | MEDIUM | Global |
| S-09 | Security | /metrics endpoint queries DB without role index guarantee | MEDIUM | app/main.py:353-358 |
| S-10 | Security | Password reset token not invalidated after use | MEDIUM | app/auth.py:178-192 |
| S-11 | Security | No rate limiting on /auth/register or /auth/login | MEDIUM | app/auth.py |
| S-12 | Security | SMTP credentials not validated at startup | LOW | app/auth.py:162 |
| A-01 | Architectural | main.py is 785-line monolith with 40+ inline routes | HIGH | app/main.py |
| A-02 | Architectural | SQLite fallback still active; no mandatory PostgreSQL enforcement | HIGH | app/database.py:8-18 |
| A-03 | Architectural | Schema migrations via ALTER TABLE instead of Alembic | HIGH | app/database.py:38-51 |
| A-04 | Architectural | No connection pooling for PostgreSQL | MEDIUM | app/database.py |
| A-05 | Architectural | /solve endpoint is synchronous blocking call to LLM | MEDIUM | app/main.py:158-278 |
| A-06 | Architectural | No SSE/streaming for LLM responses | MEDIUM | app/main.py |
| A-07 | Architectural | SuggestionEngine imported but not verified to exist | HIGH | app/main.py:263 |
| A-08 | Architectural | /genui parses JSON with regex — fragile | MEDIUM | app/main.py:135-156 |
| A-09 | Architectural | interactions table uses SQLite date() function — breaks on PostgreSQL | HIGH | app/rate_limit.py:49 |
| A-10 | Architectural | create_interaction call in /solve has malformed kwargs | CRITICAL | app/main.py:253-262 |
| A-11 | Architectural | No background task queue for async ops | MEDIUM | Global |
| A-12 | Architectural | database.py creates tables on startup — no versioned migrations | HIGH | app/database.py:53-89 |
| A-13 | Architectural | No API versioning strategy | LOW | app/main.py |
| O-01 | Operational | No structured logging (JSON) — uses print and logging.info | HIGH | Global |
| O-02 | Operational | No distributed tracing / correlation IDs | MEDIUM | Global |
| O-03 | Operational | Prometheus metrics lacks request histogram/latency | MEDIUM | app/core/prometheus_middleware.py |
| O-04 | Operational | No health check for LLM provider availability | MEDIUM | app/main.py:281-288 |
| O-05 | Operational | No automated database backups | HIGH | Global |
| O-06 | Operational | No CI/CD pipeline with security scanning | HIGH | .github/ |
| O-07 | Operational | No load testing / performance baselines | MEDIUM | Global |
| O-08 | Operational | No feature flags / kill switches | LOW | Global |
| O-09 | Operational | Redis optional but not gracefully handled | LOW | app/core/cache_middleware.py |
| B-01 | Business | Stripe webhook updates subscription without verifying stripe_customer_id | HIGH | app/billing.py:81-94 |
| B-02 | Business | No GDPR/CCPA consent tracking or data export endpoint | HIGH | Global |
| B-03 | Business | No automated pricing/checkout validation | MEDIUM | app/billing.py |
| B-04 | Business | Billing portal URL hardcoded to astrovox.ai | MEDIUM | app/main.py:752 |
| B-05 | Business | No dunning / failed payment recovery flow | MEDIUM | app/billing.py |
| B-06 | Business | create_checkout_session overwrites stripe_customer_id | LOW | app/billing.py:26-31 |
| B-07 | Business | No usage-based metering or invoice generation | MEDIUM | app/billing.py |
| T-01 | Technical Debt | requirements.txt uses == pinning without lockfile | HIGH | requirements.txt |
| T-02 | Technical Debt | No type hints in core modules (auth.py, main.py) | MEDIUM | app/auth.py, app/main.py |
| T-03 | Technical Debt | No .env validation at startup (pydantic-settings missing) | HIGH | app/config.py |
| T-04 | Technical Debt | Hardcoded model aliases in config.py instead of dynamic registry | MEDIUM | app/config.py:9-13 |
| T-05 | Technical Debt | No retry logic for transient LLM/DB/Redis failures | MEDIUM | app/core/llm.py |
| T-06 | Technical Debt | Dockerfile multi-stage build copies entire app/ without .dockerignore hygiene | LOW | Dockerfile |
| T-07 | Technical Debt | render.yaml uses free plan — not suitable for production | HIGH | render.yaml |
| T-08 | Technical Debt | No pre-commit hooks enforcing formatting/linting on PR | MEDIUM | .pre-commit-config.yaml |
| T-09 | Technical Debt | Test coverage unknown; no coverage badge or gate | MEDIUM | tests/ |
| T-10 | Technical Debt | MONTHLY.md, WEEKLY.md, DAILY.md docs not linked in README | LOW | Root |

## Master Execution Roadmap

| Tier | Theme | Objective | Timeline |
|------|-------|-----------|----------|
| 1 | Security Hardening | Eliminate all CRITICAL/HIGH security gaps | Week 1-2 |
| 2 | Architectural Refactor | Break monolith, enforce PostgreSQL, add streaming | Week 3-5 |
| 3 | Observability & Ops | Structured logging, tracing, CI/CD, backups | Week 6-7 |
| 4 | Business Readiness | Compliance, billing integrity, metering | Week 8-9 |
| 5 | Scalability & Performance | Connection pooling, caching, background tasks | Week 10-12 |
| 6 | Enterprise & Growth | Multi-tenancy, SSO, SLA, advanced agents | Week 13-16 |

## Granular Tickets — Tier 1: Security Hardening

| # | Objective | Implementation | Verification |
|---|-----------|----------------|--------------|
| 1.1 | Remove stack-trace exposure in production | Replace generic debug handler in app/main.py with production-safe JSON error responses; gate detailed errors on DEBUG env var | pytest tests/test_security.py passes; curl /health returns 200 without traceback |
| 1.2 | Enforce email verification on registration | Set email_verified=0 in app/auth.py:59; remove auto-verify fallback; add resend endpoint | Register returns 201; login before verify returns 403 |
| 1.3 | Add WebSocket authentication | Reuse get_current_user() dependency on /ws/chat/{session_id} and /ws/voice/{session_id}; reject unauthenticated connections with 401 | pytest tests/test_security.py WebSocket tests pass |
| 1.4 | Verify Stripe customer mapping | In app/billing.py handle_stripe_webhook(), fetch user by stripe_customer_id before updating subscription; log mismatches | Stripe test webhook with wrong customer_id returns 400 |
| 1.5 | Deduplicate JWT parsing in rate limiter | Decode token once at middleware entry; cache user_id + plan in request.state; remove redundant decode in app/rate_limit.py:16-26 | RateLimitMiddleware unit test asserts single jwt.decode call per request |
| 1.6 | Harden CORS origins | Load ALLOWED_ORIGINS from env/config.py; reject unmatched origins with 403; add separate production/staging lists | Config with invalid origin returns 403; valid origin returns 200 |
| 1.7 | Add CSRF protection for state-changing endpoints | Install python-csrf or fastapi-csrf; exempt /auth/token (Bearer) endpoints; require X-CSRF-Token header for cookie-authenticated routes | POST without CSRF token returns 403 |
| 1.8 | Enforce request timeouts and payload limits | Add client_max_size (e.g., 10MB) and request timeout (30s) via Starlette middleware; return 413/408 appropriately | Large payload returns 413; slow client returns 408 |
| 1.9 | Fix password reset token invalidation | Store used reset token hashes in DB; reject reused tokens in app/auth.py:185-194 | Reuse of same reset token returns 401 |
| 1.10 | Add brute-force lockout on /auth/login | Integrate existing record_failed_login() into login endpoint; block IP after 10 failures for 1 hour | 11 consecutive bad logins from same IP returns 429 |

## Continuous Iteration Policy

- **Weekly cadence:** Every Monday, run full pytest suite + coverage report; fail build if coverage drops below 80%.
- **Security triage:** Every Tuesday, run `ruff check`, `bandit`, and `pip-audit`; block PRs on HIGH/CRITICAL findings.
- **Ticket gating:** No tier advances until 100% of its tickets have passing verification steps in CI.
- **Rollback discipline:** Every Tier deployment uses blue/green with instant rollback on error-rate spike (>5% 5xx for 2 minutes).
- **Documentation sync:** AUDIT_AND_ROADMAP.md is updated at end of each tier; deprecated tickets move to archive section.
- **Metrics review:** Weekly review of /metrics (request latency, error rate, LLM cost per request) with alerting thresholds defined in Tier 3.
