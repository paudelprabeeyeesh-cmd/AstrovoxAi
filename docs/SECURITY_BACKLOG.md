# Security & Readiness Backlog

Tracks the security and reliability work that the product roadmap does
not cover. Status is stated as measured, not as intended.

Legend: **[x]** done and tested · **[~]** done but unverified in this
environment · **[ ]** open

## Group 1 — Critical security (audit findings)

| Item | Status | Where |
|---|---|---|
| Tokens returned in API responses | [x] | `app/services/token_mailer.py`; verification and reset tokens are emailed only |
| `/auth/refresh` token in query string | [x] | Body field only; `test_refresh_token_rejected_as_query_parameter` guards it |
| `oauth_login` ignored its access token | [x] | Provider allowlist + userinfo verification, session bound to the verified subject |
| `auth.py` imports at file bottom, dead code after `raise`, duplicate defs | [x] | Single `get_current_user`, single `require_admin`, imports at top |
| 30 silent `except Exception` router stubs | [x] | `app/router_loader.py`, logs module + exception + correlation id, serves 503 |
| Redis URL had no password in prod compose | [x] | `docker-compose.prod.yml`; guarded by the `compose-smoke` CI job |
| `.env` tracked in git | [x] | Removed from the index; `.gitignore` covers it; see `docs/SECRET_ROTATION.md` |
| Fake CI coverage gate | [x] | Parses the real coverage XML and can fail |

## Group 2 — Infrastructure

| Item | Status | Where |
|---|---|---|
| Both Dockerfiles unbuildable (fake digests, distroless `RUN`, `tini` absent) | [x] | Rewritten; tini installed, non-root, wheels-only runtime |
| nginx fake `$csp_nonce` | [x] | Removed; CSP has no nonce and no `unsafe-inline` in `script-src` |
| nginx header inheritance | [x] | Headers in `nginx/snippets/security-headers.conf`, included by every location |
| Hardcoded nginx domains | [x] | Rendered from a template by `docker/frontend-entrypoint.sh` |
| Redis/Prometheus/Grafana host bindings | [x] | `docker-compose.override.yml` binds to `127.0.0.1` only |
| Container hardening on prod compose | [x] | `cap_drop`, `read_only`, `tmpfs` still absent on some services |
| Real TLS with certs | [ ] | TLS is terminated at the edge; no certbot in the stack |

## Group 3 — Correctness

| Item | Status | Where |
|---|---|---|
| `get_db` shim always raised | [x] | `app/database.py` delegates to the repository layer |
| 11 raw-SQL call sites in `auth_service.py` | [x] | `text()` + named params + `with get_db() as conn:` |
| `login_attempts` schema split across two modules | [x] | `app/services/login_attempt_schema.py` |
| `refresh_token_rotation` self-deadlock | [x] | `RLock` instead of `Lock` |
| `ip_filter` refused every non-parseable client host | [x] | Only enforced when a list is configured |
| Health probes blocked by IP/UA middleware | [x] | `/health`, `/metrics`, `/docs` exempt |
| `record_failure` returned 3-tuple, tests read 2 | [x] | Test updated to the real contract |
| 7 dead subsystems (enterprise/support/white_label/rag/performance) | [x] | Import bugs fixed, `memory_consolidation` router added |
| Duplicate `include_router` calls mounting routes twice | [x] | Four removed |
| Full Python suite baseline recorded | [x] | `docs/BASELINE.md`, 123 security tests green |
| `get_conversation` unscoped query | [x] | `user_id` required; found by `test_tenant_isolation_data.py` |

## Group 4 — Product proof

| Item | Status | Where |
|---|---|---|
| 8-case golden set | [x] | `evals/golden_set.py` |
| 105-case set with stable held-out split | [x] | `evals/expanded_set.py`, split asserted stable across processes |
| Eval regression gate in CI | [x] | `evals/eval_gate.py`, `eval-gate` job |
| Cross-tenant isolation on the data path | [x] | `tests/security/test_tenant_isolation_data.py`, 30 tests |
| Cross-tenant isolation in the database (RLS) | [x] | `supabase/migrations/20261012013000_rls_tenant_isolation.sql`; 11 tables, coverage test in `tests/security/test_rls_migration.py` |
| E2E for the five core flows | [~] | `tests/e2e/core-path.spec.js` written and syntax-valid, **never executed** (no browser, no `node_modules`) |
| Redis-backed bounded rate limiter | [~] | In-process limiter is now capped; Redis-backed when `REDIS_URL` is set |
| Server-side AI spend cap | [x] | `app/ai_spend_cap.py`, wired into `/chat/message` |
| Spend cap on the embeddings path | [x] | `app/embedding_spend.py`, input-only pricing |
| Container hardening on prod compose | [x] | cap_drop ALL, no-new-privileges, read_only + tmpfs, non-root uid on all 7 services |

## Group 5 — Honesty items

| Item | Status | Where |
|---|---|---|
| "Production Readiness 95%" and "Telemetry 100%" claims | [x] | Removed from README; `docs/BASELINE.md` states what was broken |
| Self-assigned titles ×9 | [x] | Absent; checked, nothing to remove |
| Lovable/Devin/Copilot as 3 of 5 contributors | [x] | Stated in README's Maintainer and provenance section rather than hidden; history cannot be rewritten per `AGENTS.md` |
| No SECURITY.md | [x] | Written, with reporting path and known gaps |
| Frontend build secret audit | [x] | `frontend-secret-audit` CI job |
| Go engine benchmarked against llama.cpp / vLLM | [ ] | Stated as unbenchmarked in README; the benchmark is unwritten |
| "Impossible mode" package count as differentiator | [x] | Explicitly not claimed; README says so |

## Open, in priority order

1. **Execute the RLS migration.** The policies are written and their coverage
   is tested, but no Postgres was available here, so they have not been
   applied to real rows. `supabase db push` against staging, then the
   two-role query in `queries/rls_tenant_isolation.sql`.
2. **`test_core_flows.py` (17 errors) and `test_lifecycle.py` (11 failures).**
   Triaged by group, not root-caused individually.
3. **Execute the E2E.** Install playwright and a browser, confirm the
   selectors and the auth-storage keys that `core-path.spec.js` assumes.
4. **Cost cap on agents and RAG synthesis.** Embeddings and chat are gated;
   the other two AI paths still record nothing.
5. **The Go engine benchmark.** Write the build-versus-adopt decision and
   measure against llama.cpp or vLLM on a real model.
6. **`redis` runs with a tmpfs `/data`.** A consequence of `read_only: true`;
   persistence is discarded on restart. Right for a cache, wrong for a
   session store, and it needs a volume-based decision before this is
   deployed for keeps.
