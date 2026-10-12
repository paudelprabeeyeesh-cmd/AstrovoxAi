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
| Container hardening on prod compose | [ ] | `cap_drop`, `read_only`, `tmpfs` still absent on some services |
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
| Cross-tenant isolation in the database (RLS) | [ ] | No RLS policies exist; the app layer is asserted, the DB layer is not |
| E2E for the five core flows | [~] | `tests/e2e/core-path.spec.js` written and syntax-valid, **never executed** (no browser, no `node_modules`) |
| Redis-backed bounded rate limiter | [~] | In-process limiter is now capped; Redis-backed when `REDIS_URL` is set |
| Server-side AI spend cap | [x] | `app/ai_spend_cap.py`, wired into `/chat/message` |

## Group 5 — Honesty items

These are the ones that matter for the story above them.

| Item | Status | Where |
|---|---|---|
| "Production Readiness 95%" and "Telemetry 100%" claims | [ ] | Both Dockerfiles were unbuildable and the backend could not reach Redis; those numbers are not defensible |
| Self-assigned titles ×9 | [ ] | Should read "Founder & Full-stack developer" |
| Lovable/Devin/Copilot as 3 of 5 contributors | [ ] | Fine for scaffolding; signals a codebase without human security review, which the findings above confirm |
| No SECURITY.md | [x] | Written, with reporting path and known gaps |
| No CHANGELOG | [ ] | |
| No gitleaks on the frontend build | [x] | `frontend-secret-audit` CI job |
| Go engine benchmarked against llama.cpp / vLLM | [ ] | The build-vs-adopt decision is unwritten |
| "Impossible mode" package count used as a differentiator | [ ] | Package counts appear in no customer's buying decision |

## Open, in priority order

1. **RLS policies in Postgres.** The app layer enforces tenant scoping; the
   database does not. One missed call site is a cross-tenant read.
2. **`test_core_flows.py` (17 errors) and `test_lifecycle.py` (11 failures).**
   Triaged by group, not root-caused individually.
3. **Execute the E2E.** Install playwright and a browser, confirm the
   selectors and the auth-storage keys that `core-path.spec.js` assumes.
4. **Container hardening** on the remaining prod-compose services.
5. **Cost cap on the non-chat AI paths** (embeddings, agents, RAG
   synthesis).
6. **The honesty items.** They are the cheapest on the list and the most
   visible to a reader who knows the area.
