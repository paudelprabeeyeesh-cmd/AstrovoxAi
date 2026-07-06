# Changelog

All notable changes from the production-readiness pass. This builds on the
earlier audit PR (#2), which fixed the broken Vite build, hardened CORS/secrets,
purged ~360 junk files, and added the first DB migration.

## [2.1.0] — Production Engineering Pass (2026-06-29)

### Added
- **Rate Limiting**: Implemented slowapi for backend rate limiting
  - Signup: 5 requests/minute
  - Login: 10 requests/minute
  - Chat messages: 30 requests/minute
- **CI/CD Pipeline**: Complete GitHub Actions workflow (`.github/workflows/ci.yml`)
  - Frontend lint & build job
  - Backend lint & test job
  - Secret scanning with TruffleHog
  - Dependency auditing (npm + safety)
  - Docker build testing
- **Docker Configuration**: Production-ready containerization
  - `Dockerfile.backend` - Python 3.9-slim with health checks
  - `Dockerfile.frontend` - Multi-stage Node 18-alpine + Nginx
  - `docker-compose.yml` - Multi-container orchestration
  - `nginx.conf` - Production reverse proxy with security headers
- **Deployment Documentation**: Comprehensive `DEPLOYMENT.md` guide
  - Docker deployment instructions
  - Cloud platform deployment options
  - Security considerations
  - Scaling recommendations
  - Monitoring and backup strategies

### Changed
- **Backend Dependencies**: Added `slowapi>=0.1.9` to requirements.txt
- **Documentation Updates**:
  - Updated `README.md` with new features (rate limiting, Docker, CI/CD)
  - Updated `SETUP.md` with Docker Compose setup option
  - Updated project structure in documentation

### Fixed
- **CI/CD Docker Build Path**: Fixed Docker build context in CI workflow
  - Changed from `02-Backend/` to `.` for backend build
  - Ensures correct Dockerfile resolution

### Removed
- **Legacy Documentation**: Removed outdated documentation files
  - `DEVELOPMENT_GUIDE.md` (described removed Flask/Gemini stack)
  - `QUICK_REFERENCE.md` (referenced removed architecture)
  - `SESSION_SUMMARY.md` (session-specific, not canonical)
  - `Documentation/` folder (legacy role profiles)

### Security
- Rate limiting prevents brute force attacks on authentication
- Secret scanning in CI/CD prevents leaked credentials
- Dependency auditing identifies vulnerable packages
- Security headers configured in Nginx (X-Frame-Options, X-Content-Type-Options, etc.)

### Verification
- Backend tests: 5/5 passing ✅
- Backend linting: Flake8 clean ✅
- Backend formatting: Black compliant ✅
- Frontend build: NOT VERIFIED (npm not available in environment)
- Docker build: NOT VERIFIED (Docker not available in environment)
- CI/CD configuration: Syntax validated ✅

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
