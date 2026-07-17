# Changelog

All notable changes from the production-readiness pass. This builds on the
earlier audit PR (#2), which fixed the broken Vite build, hardened CORS/secrets,
purged ~360 junk files, and added the first DB migration.

## [Unreleased]

### Changed
- Replaced the generic feature list with a delivery-gated Astrovox AI product
  roadmap. It defines the AI Workspace Foundation, conversation workspace,
  project workbench, trusted knowledge/memory, supervised agent runtime,
  enterprise platform, and the measurable definition of 100% completion.
- Updated the README to distinguish current capabilities from planned work and
  link the delivery roadmap.

## [2.0.0] — Production-readiness pass

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
