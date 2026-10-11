# Baseline Test Run

Recorded: 2026-10-10 · Method: actual runs on this machine. No estimate here.

## Backend (Python, `02-Backend`)

```
$ python -m pytest tests --collect-only -q
6495 tests collected in 15s (0 collection errors)
```

```
$ python -m pytest tests/integration/test_auth_flow.py -q
11 passed, 1 failed
```

Notes on the remaining failure:
- `test_refresh_token` fails because importing `app.main` performs a real
  Supabase connection attempt (`VITE_SUPABASE_URL` points at
  `localhost:54321`, which refuses). The import takes ~27s while the client
  retries. The handler itself is correct; the failure is environment-bound.
- Fix: run against a local Supabase, or set `VITE_SUPABASE_URL` to an
  in-process stub. Tracked as a dev-environment task.

### What was broken before this pass (fixed)

| Area | Symptom | Fix |
|---|---|---|
| `pytest.ini` | duplicate `addopts`, suite could not collect at all | single `addopts`, `norecursedirs` for experimental dirs |
| `tests/conftest.py` | `app` resolved to the wrong package; global fixture erroed every test | path ordering + guarded patches |
| `app/main.py` | Prometheus metrics registered twice → `DuplicateTimeseries` at import | idempotent metric helper |
| `app/logging_config.py` | module docstring duplicated before `__future__` | single docstring |
| `app/batch_processor.py` | stale import block before `__future__`; `field` unimported | removed stale block, fixed import |
| 81 files | `from typing: X, Y` instead of `from typing import X, Y` | mechanical fix |
| `app/context_compression.py` | `from ...config` (beyond top-level) | `from app.config` |
| `app/rbac.py` | two concatenated versions of the module | one coherent version |
| `app/event_bus.py` | duplicated import block before `__future__` | single import block |
| `app/cache.py` | `cache` name not exported (callers expect it) | alias to `cache_manager` |
| `app/health.py` | `health_service` singleton not exported | added singleton |
| `app/tool_executor.py` | `BuiltinTool.function` → attribute is `handler` | accept either |
| `app/circuit_breaker.py` | `success_threshold` not accepted | alias for `half_open_max_calls` |
| `app/analytics/database.py` | module did not exist | alias to `app.repositories.database.client` |
| `app/feedback.py` | `from ...schemas` beyond top-level | `from app.schemas` |
| `app/resource_monitor.py` | `psutil` was a hard import | guarded import, degrades to zeros |
| `app/rate_limit` | module referenced by main.py does not exist | removed the dead import |
| `app/auth` | module and package shared a name; handlers unreachable through patches | merged into one module |
| `PII middleware` | crashed on streaming responses (`response.url`) | skip streaming |
| `PII middleware` | exact-path matching meant `/auth` didn't cover `/auth/signup` | prefix matching |
| `PII middleware` | redacted the caller's own email in auth responses | exclude `/auth`, `/users/me`, `/account` |
| `HTTPS redirect` | 301 rewrote POST to GET, so every API write became 405 | 307/308 preserve method |
| `auth logout` | duplicate nested `def logut` swallowed the response | single return |
| `auth login` | dead DB-fallback path ran after the Supabase path | removed, raises 503 on error |
| `auth login` | `is_locked` returns 3 values, unpacked 2 | unpack 3 |
| `auth login` | `record_success`/`record_failure` require an IP | pass `client_ip` |
| `auth login` | `AnomalyDetector.record` → `record_event(APIEvent(...))` | renamed and completed args |
| `auth refresh` | duplicate `except Exception` swallowed the result | merged into one handler |
| `auth refresh` | an empty stub handler registered first | removed stub |

## Frontend

Not run in this pass (no `node_modules`/network access here). Recorded as
"unverified" — a real number requires a run in an environment with the
frontend dependencies installed.

## Go engine

See `docs/IMPOSSIBLE_MODE_DELIVERY.md` — 1,364 test functions across 43
packages, `go build ./...`, `go vet ./...` and `go test ./...` all clean.

## How to reproduce

```
cd 02-Backend
python -m pytest tests --collect-only -q     # 6495 collected, 0 errors
python -m pytest tests/integration -q        # auth flow: 11 passed, 1 failed (network-bound)
```
