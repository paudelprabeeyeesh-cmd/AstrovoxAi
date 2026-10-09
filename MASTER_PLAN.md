# AstrovoxAI — Master Execution Plan
**Generated:** 2026-09-24  
**Owner:** Master Planner  
**Scope:** Backend, Frontend, Tests, Docs, Infra  
**Status:** ACTIVE

---

## Executive Summary

AstrovoxAI is a functional prototype with substantial implementation across 9 phases. The codebase is large but not production-hardened. Critical gaps remain in security, architectural modularity, test coverage with live services, and verified deployment. This plan decomposes remaining work into 6 tiers with granular tasks, acceptance criteria, and exact file targets.

---

## Current State Snapshot

| Domain | Status | Blockers |
|--------|--------|----------|
| Frontend (Vite) | 100% impl, 95% lint/typecheck | `src/` unused; primary is `apps/web/` |
| Frontend (Next.js) | 95% impl | Needs routing consolidation |
| Backend | 90% impl | `main.py` monolith; 32 tests blocked on DB |
| Tests | 41/73 passing | PostgreSQL required for 32 tests |
| Security | Partial | Stack traces, WebSocket auth, CORS hardening |
| Infra | Partial | Staging not provisioned; production not deployed |
| Docs | 95% complete | Needs sync with code changes |

---

## Tier 0 — Foundation Unblock (Week 1)

**Objective:** Eliminate all blockers preventing local and CI execution.

| ID | Task | Target Path | Acceptance Criteria | Quality Gate |
|----|------|-------------|---------------------|--------------|
| 0.1 | Provision PostgreSQL locally | `docker-compose.yml` | `docker compose up postgres -d` succeeds; `psql` connects | `pg_isready -h localhost -p 5432` returns true |
| 0.2 | Run database migrations | `database/schemas/supabase_setup.sql` | All tables created; `\dt` shows users, chats, messages, embeddings, audit_logs | `pytest tests/test_database.py -v` passes |
| 0.3 | Unblock 32 DB-dependent tests | `02-Backend/tests/conftest.py` | Full suite: `pytest tests/ -v` — 100% collection; ≥80% pass | Coverage report ≥80% |
| 0.4 | Fix `main.py` import errors | `02-Backend/app/main.py` | `python -c "import app.main"` exits 0; no ImportError | `python -m py_compile app/main.py` |
| 0.5 | Validate all Dockerfiles build | `Dockerfile.backend`, `Dockerfile.frontend` | `docker build -f Dockerfile.backend .` succeeds; image <2GB | `docker images` shows healthy size |
| 0.6 | Enable pre-commit hooks | `.pre-commit-config.yaml` | `pre-commit run --all-files` exits 0 | CI fails on unformatted code |

---

## Tier 1 — Security Hardening (Week 2-3)

**Objective:** Eliminate all CRITICAL/HIGH gaps from `AUDIT_AND_ROADMAP.md`.

| ID | Task | Target Path | Acceptance Criteria | Quality Gate |
|----|------|-------------|---------------------|--------------|
| 1.1 | Remove stack-trace exposure | `02-Backend/app/main.py` | `DEBUG=false` returns JSON `{detail:...}`; no traceback in `/health` | `curl /health` under `DEBUG=false` shows no Python frames |
| 1.2 | Enforce email verification | `02-Backend/app/auth.py` | Register sets `email_verified=false`; login returns 403 before verify | `test_auth.py::test_email_verified_block` passes |
| 1.3 | Add WebSocket JWT auth | `02-Backend/app/main.py` (WS routes) | `/ws/chat/{id}` rejects without token; accepts with valid Bearer | `test_websocket.py::test_auth_required` passes |
| 1.4 | Verify Stripe customer mapping | `02-Backend/app/billing.py` | Webhook with mismatched `stripe_customer_id` returns 400 | `test_billing.py::test_stripe_customer_mismatch` passes |
| 1.5 | Deduplicate JWT parsing | `02-Backend/app/rate_limit.py` | Single `jwt.decode` per request; user_id cached in `request.state` | Mock asserts `decode.call_count == 1` |
| 1.6 | Harden CORS origins | `02-Backend/app/config.py`, `main.py` | Invalid origin returns 403; valid returns 200; env-driven list | `test_cors.py::test_invalid_origin_blocked` passes |
| 1.7 | Add CSRF protection | `02-Backend/app/security/` | State-changing POST without token returns 403; Bearer exempt | `test_security.py::test_csrf_protection` passes |
| 1.8 | Enforce request timeouts/payload limits | `02-Backend/app/main.py` | Payload >10MB returns 413; slow client returns 408 | `test_security.py::test_payload_limit` passes |
| 1.9 | Invalidate password reset tokens | `02-Backend/app/auth.py` | Reused reset token returns 401; hash stored in DB | `test_auth.py::test_reset_token_reuse_blocked` passes |
| 1.10 | Add brute-force lockout | `02-Backend/app/auth.py`, `rate_limit.py` | 11 bad logins from same IP returns 429 for 1h | `test_auth.py::test_brute_force_lockout` passes |

---

## Tier 2 — Architectural Refactor (Week 4-5)

**Objective:** Break monolith, enforce PostgreSQL, add streaming.

| ID | Task | Target Path | Acceptance Criteria | Quality Gate |
|----|------|-------------|---------------------|--------------|
| 2.1 | Split `main.py` into routers | `02-Backend/app/routers/` | `main.py` <500 lines; all routes in `routers/` submodules | `pytest tests/ -v` — 100% pass |
| 2.2 | Enforce PostgreSQL (remove SQLite fallback) | `02-Backend/app/database.py` | `DATABASE_URL` missing raises `RuntimeError` at startup | `test_database.py::test_postgres_only` passes |
| 2.3 | Add Alembic migrations | `02-Backend/alembic/` | `alembic upgrade head` creates schema; `alembic revision` generates migration | `alembic current` shows head |
| 2.4 | Add connection pooling | `02-Backend/app/database.py` | `pgbouncer` or `SQLAlchemy` pool; max connections enforced | Load test: 100 concurrent connections without exhaustion |
| 2.5 | Implement SSE streaming for chat | `02-Backend/app/chat.py` | `POST /chat/stream` returns `text/event-stream`; tokens arrive incrementally | `test_chat_stream.py` passes; p99 <2s for first token |
| 2.6 | Add background task queue | `02-Backend/app/workers/` | `ARQ` or `Celery` worker processes async jobs (email, analytics) | `test_workers.py::test_async_job` passes |
| 2.7 | Remove dead AI modules or wire them | `02-Backend/app/` | No `ImportError` on `import app.main`; unused modules deleted or documented | `pytest tests/ -v` — 0 import errors |
| 2.8 | Add pagination to list endpoints | `02-Backend/app/routers/` | `GET /chat/conversations?limit=20&offset=0` returns paginated response | `test_pagination.py` passes |

---

## Tier 3 — Observability & Ops (Week 6-7)

**Objective:** Structured logging, tracing, CI/CD, backups verified.

| ID | Task | Target Path | Acceptance Criteria | Quality Gate |
|----|------|-------------|---------------------|--------------|
| 3.1 | Enforce structured JSON logging | `02-Backend/app/core/structured_logging.py` | All logs emit JSON with `request_id`, `level`, `message` | `grep "{" logs/*.log` shows valid JSON |
| 3.2 | Add distributed tracing | `02-Backend/app/core/tracing.py` | Jaeger UI shows traces for `/chat/message` | `curl localhost:16686` shows service |
| 3.3 | Add request histogram/latency metrics | `02-Backend/app/core/prometheus_middleware.py` | `/metrics` includes `http_request_duration_seconds` histogram | `curl /metrics | grep histogram` returns data |
| 3.4 | Verify CI/CD pipeline green | `.github/workflows/ci.yml` | All jobs pass on `main`; lint, test, security-scan green | GitHub Actions badge shows passing |
| 3.5 | Implement automated backups | `02-Backend/scripts/backup_db.py` | Daily `pg_dump` to S3/R2; restore tested in staging | Restore from backup succeeds in <30min |
| 3.6 | Add health check for LLM providers | `02-Backend/app/health.py` | `/health` returns `{"openai": "ok", "anthropic": "ok"}` | `test_health.py::test_llm_provider_health` passes |
| 3.7 | Add feature flags | `02-Backend/app/config.py` | `ENABLE_STREAMING=false` disables stream endpoint | `test_feature_flags.py` passes |

---

## Tier 4 — Business Readiness (Week 8-9)

**Objective:** Compliance, billing integrity, metering.

| ID | Task | Target Path | Acceptance Criteria | Quality Gate |
|----|------|-------------|---------------------|--------------|
| 4.1 | Add GDPR/CCPA consent tracking | `02-Backend/app/compliance.py` | Consent state stored; export endpoint returns user data | `test_compliance.py::test_data_export` passes |
| 4.2 | Add dunning / failed payment recovery | `02-Backend/app/billing.py` | Failed payment triggers email; subscription suspended after 3 failures | `test_billing.py::test_dunning_flow` passes |
| 4.3 | Implement usage-based metering | `02-Backend/app/usage.py` | Token usage tracked per user; invoice generated monthly | `test_usage.py::test_metering` passes |
| 4.4 | Add SOC 2 audit log | `02-Backend/app/audit.py` | Sensitive actions (login, payment, data export) logged immutably | `test_audit.py::test_immutable_log` passes |
| 4.5 | Fix billing portal URL hardcoding | `02-Backend/app/main.py` | Portal URL from env `FRONTEND_URL`; not hardcoded | `test_billing.py::test_portal_url` passes |

---

## Tier 5 — Scalability & Performance (Week 10-12)

**Objective:** Connection pooling, caching, background tasks productionized.

| ID | Task | Target Path | Acceptance Criteria | Quality Gate |
|----|------|-------------|---------------------|--------------|
| 5.1 | Add Redis caching layer | `02-Backend/app/cache.py` | Session cache hit rate >80%; response cache for `/api/stats` | `test_cache.py::test_hit_rate` passes |
| 5.2 | Optimize p99 latency | `02-Backend/app/chat.py` | p99 <500ms for non-streaming; <2s for streaming first token | Load test: 100 concurrent users |
| 5.3 | Add rate limiting on all public endpoints | `02-Backend/app/rate_limit.py` | `/auth/register` and `/auth/login` have explicit limits | `test_rate_limiter.py` passes |
| 5.4 | Productionize fine-tuning pipeline | `02-Backend/app/fine_tuning.py` | Pipeline runs end-to-end with test model; metrics logged | `test_finetune_pipeline.py` passes |
| 5.5 | Add API versioning | `02-Backend/app/routers/` | `/v1/chat/message` and `/v2/chat/message` coexist | `test_api_versioning.py` passes |

---

## Tier 6 — Enterprise & Growth (Week 13-16)

**Objective:** Multi-tenancy, SSO, SLA, advanced agents.

| ID | Task | Target Path | Acceptance Criteria | Quality Gate |
|----|------|-------------|---------------------|--------------|
| 6.1 | Implement multi-tenancy | `02-Backend/app/tenants.py` | Organizations isolated by `tenant_id`; no cross-tenant data leak | `test_tenant_isolation.py` passes |
| 6.2 | Add SSO (SAML/OIDC) | `02-Backend/app/sso.py` | SSO login creates/links user; logout redirects to IdP | `test_sso.py` passes |
| 6.3 | Add SLA monitoring | `02-Backend/app/slo.py` | Alerts fire when error rate >0.1% or p99 >1s for 5min | Prometheus alert rules present |
| 6.4 | Build plugin marketplace | `02-Backend/app/plugin_marketplace.py` | Plugin CRUD; sandboxed execution; versioning | `test_plugin_framework.py` passes |
| 6.5 | Add advanced agent orchestration | `02-Backend/app/agents/` | Multi-agent workflow executes; tools registered; memory shared | `test_multi_agent.py` passes |

---

## Execution Order & Dependencies

```
Tier 0 (Foundation Unblock)
  │
  ├──► Tier 1 (Security Hardening)
  │       │
  │       └──► Tier 2 (Architectural Refactor)
  │               │
  │               └──► Tier 3 (Observability & Ops)
  │                       │
  │                       └──► Tier 4 (Business Readiness)
  │                               │
  │                               └──► Tier 5 (Scalability)
  │                                       │
  │                                       └──► Tier 6 (Enterprise)
```

**Parallel tracks:**
- Frontend (`apps/web/`) can proceed independently from Tier 0-2
- Docs sync with each tier completion
- Security audit runs in parallel with Tier 1

---

## Quality Gates (Global)

| Gate | Threshold | Enforcement |
|------|-----------|-------------|
| Test Coverage | ≥80% | CI fails if `coverage < 80` |
| Lint | 0 errors, 0 warnings | `npm run lint`, `ruff check` in CI |
| TypeCheck | 0 errors | `npm run typecheck` in CI |
| Security Scan | 0 HIGH/CRITICAL | `bandit`, `pip-audit` in CI |
| Build Time | <10s | `npm run build` in CI |
| p99 Latency | <500ms | Load test in CI on staging |
| Dependency freshness | No critical CVEs | `npm audit`, `safety check` weekly |

---

## Weekly Cadence

| Day | Activity |
|-----|----------|
| Mon | Tier planning; full pytest + coverage |
| Tue | Lint, bandit, pip-audit; block PRs on HIGH/CRITICAL |
| Wed | Implementation day |
| Thu | Implementation day; mid-tier review |
| Fri | Integration test; tier gate review |
| Sat | Buffer / bug fixes |
| Sun | Rest |

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Test pass rate | 100% of collected tests | `pytest tests/ -v` |
| Test coverage | ≥80% | `pytest --cov` |
| Security findings | 0 HIGH/CRITICAL | `bandit -r 02-Backend/app -ll` |
| p99 latency | <500ms | Locust/k6 load test |
| Uptime | 99.9% | Pingdom / UptimeRobot |
| Deployment frequency | Weekly | GitHub Actions |
| MTTR | <1h | Incident tracking |

---

## Immediate Next Actions (This Week)

1. **Provision PostgreSQL:** `docker compose up -d postgres redis`
2. **Run migrations:** `psql -U astrovox -d astrovox -f database/schemas/supabase_setup.sql`
3. **Unblock tests:** Set `DATABASE_URL` and run `pytest tests/ -v`
4. **Fix `main.py` imports:** Ensure `python -c "import app.main"` succeeds
5. **Begin Tier 1.1:** Remove stack-trace exposure in `app/main.py:123-132`

---

*Plan generated by Master Planner. Update after each tier completion.*
