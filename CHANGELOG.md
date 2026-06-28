# Changelog

All notable changes from the production-readiness pass. This builds on the
earlier audit PR (#2), which fixed the broken Vite build, hardened CORS/secrets,
purged ~360 junk files, and added the first DB migration.

## [Unreleased] — Production hardening pass (builds on PR #3)

### Added
- **CI/CD** — `.github/workflows/ci.yml` runs on push/PR to `main`: frontend
  build (`npm ci` + `npm run build`), backend lint + tests (`flake8` + `pytest`),
  and a **gitleaks** secret scan.
- **Rate limiting** — `slowapi` per-client-IP limiter on all endpoints, default
  `120/minute`, configurable via `RATE_LIMIT`. Returns HTTP 429 when exceeded.
- **Structured logging** — `app/logging_config.py` (`configure_logging`, level via
  `LOG_LEVEL`). Replaced all 15 `print(...)` error statements in `database.py`
  with a module `logger`.
- **Input validation** — pydantic `Field` constraints: chat `message`
  (1–8000 chars), `model`/`title` length caps, memory `content` (1–4000) and
  `importance` (1–5). Invalid bodies now return 422 instead of failing deeper.
- **Deployment** — `02-Backend/Dockerfile` (non-root user, healthcheck) +
  `.dockerignore`; new `DEPLOYMENT.md` (env vars, DB, Docker, frontend, CI,
  security checklist).
- **Tests** — `tests/test_validation.py` (4 cases). Suite now **9 tests pass**.

### Fixed
- **Exception-swallowing bug** in `memory.auto_extract_memory`: a generic
  `except Exception` re-wrapped the "OpenAI not configured" `HTTPException` as a
  500. Added `except HTTPException: raise`.

### Changed
- `README.md` corrected (removed non-existent TailwindCSS; added setup, DB,
  CI, deployment sections). `.env.example` dropped unused `USE_MOCK_AI` /
  `SECRET_KEY` and documented `LOG_LEVEL` / `RATE_LIMIT`.

### Deferred (documented, not safe to apply)
- **esbuild dev-server advisory (GHSA-67mh-4wv8-2f99, moderate).** Only affects
  the Vite dev server, never production builds. The npm-proposed fix upgrades
  Vite 5 → 8 (rolldown), which **breaks `npm run build`** (verified — reverted).
  Tracked for a deliberate framework-upgrade PR.

### Verification (this pass)
- `npm run build` → ✅ (81 modules, exit 0)
- `python -m flake8 app tests` → ✅ clean
- `python -m pytest -q` → ✅ 9 passed
- backend boot + live `/health`, `/`, `/api/me` (401), `/docs` → ✅
- `npm audit` → 2 advisories remain (Vite/esbuild dev-server only; see Deferred)
- `docker build` of the new Dockerfile → **NOT VERIFIED** (no Docker in this environment)

---

## [Unreleased] — Production-readiness pass

### Fixed
- **Backend could not start (P0).** `app/main.py` used top-level imports
  (`from auth import …`) that fail under the documented run command
  `uvicorn app.main:app`. Converted all backend modules to package-relative
  imports (`from .auth import …`) and added `app/__init__.py`. The server now
  boots; verified `/health`, `/health/readiness`, `/health/liveness`, `/`, `/docs`.
- **User memory was built but never used (bug).** `chat.send_message` assembled
  `memory_context` from `ai_memory` then discarded it. It is now prepended as a
  `system` message so stored memory actually influences AI responses.
- **Deprecated API.** Replaced `datetime.utcnow()` (deprecated in 3.12) with
  `datetime.now(timezone.utc)` in `main.py` and `api.py`.
- **Lint.** Resolved all `flake8` findings (unused imports/vars, formatting);
  repo is now `flake8`-clean under `02-Backend/setup.cfg` and `black`-formatted.

### Changed
- **Single Supabase client (performance).** Added `app/supabase_client.py`
  (`lru_cache`d `get_supabase()`). `auth.py`, `database.py`, and the auth helper
  now reuse one client instead of constructing a new one **per request**.
- **Shared auth dependency (DRY).** Added `app/auth_utils.py`; removed the
  `get_user_id_from_token` function that was duplicated verbatim in
  `chat.py`, `api.py`, and `memory.py`.
- Tightened broad `except Exception as e` handlers that swallowed `HTTPException`
  (auth `/me`, `/refresh`) so specific 401 reasons are preserved.

### Added
- `02-Backend/tests/` smoke suite (`test_health.py` + `conftest.py`) covering
  health endpoints, root, and that a protected route returns 401 without auth.
  **5 tests pass.**
- `02-Backend/setup.cfg` (flake8 config, `max-line-length=120`).
- `CHANGELOG.md`, `CLEANUP_REPORT.md`; refreshed `AUDIT_REPORT.md`.

### Removed
- **337 files** of proven-unused legacy/duplicate code and broken configs
  (full proof in `CLEANUP_REPORT.md`). Tracked files: 374 → 44.
- Unused `google-generativeai` dependency from `requirements.txt`.

### Security (unchanged — still requires owner action)
- The Gemini API key previously committed at `AI-Integration/ai-logic/.env`
  remains in **git history** and MUST be rotated. Removing the file does not
  scrub history. See `AUDIT_REPORT.md`.

### Verification
- `npm run build` → ✅ (81 modules, exit 0)
- `python -m flake8 app tests` → ✅ clean
- `python -m pytest -q` → ✅ 5 passed
- `uvicorn app.main:app` boot + live health checks → ✅
- DB migration executed against a live Supabase instance → **NOT VERIFIED**
  (no Supabase credentials in this environment; SQL is idempotent + syntax-reviewed).
