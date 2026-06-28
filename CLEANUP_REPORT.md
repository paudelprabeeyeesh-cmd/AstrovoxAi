# CLEANUP REPORT — AstroVoxAI

This report lists every file/folder removed in the production-readiness pass and
the proof that it was unused by the **canonical stack**:

> **Canonical stack** = Vite/React (`src/`) → FastAPI (`02-Backend/app/`) → Supabase Postgres
> Entry points: `index.html` → `/src/main.jsx`; `package.json` `backend` script → `uvicorn app.main:app`.

**Total removed: 337 tracked files. Tracked files: 374 → 44.**

## Method of proof

For every candidate the following references were searched and found **empty**:
- `index.html` script/style references (only `/src/main.jsx`).
- `package.json` scripts (`vite` + `uvicorn app.main:app` only).
- Imports inside `src/**` (no imports of `js/`, `css/`, `01-Frontend/`, `astravox-ai/`, etc.).
- Imports inside `02-Backend/app/**` (only relative `.` imports + third-party libs).

Verification after removal: `npm run build` ✅, `uvicorn app.main:app` imports (12 routes) ✅, `pytest` ✅.

## Removed — alternate / parallel architectures (not the canonical stack)

| Path | Files | What it was | Proof unused |
|---|---|---|---|
| `astravox-ai/` | 215 | Separate Express mini-app **incl. committed `node_modules/`** | Not referenced by `index.html`/`package.json`; self-contained second app |
| `AI-Integration/`, `03-AI-Integration/` | 25 | Parallel Google-Gemini Python stack | Not imported by `02-Backend/app/` (uses OpenAI); contained a **leaked key** (already untracked in PR #2) |
| `js/`, `css/` | 30 | Legacy vanilla-JS frontend + stylesheets | Only referenced by removed `error.html`/`dashboard.html` (broken `../` paths) |
| `01-Frontend/` | 10 | Older static HTML/CSS/JS frontend | Not the Vite entry; no references |
| `ui/`, `data/`, `api/` | 19 | **Kotlin** desktop/Android app (`.kt`) | Wrong language/runtime; not built by Vite or FastAPI |
| `voice-ai/` | 1 | Standalone speech-recognition JS | No references |
| `Backend/`, `routes/` | 6 | Express/Flask backends | Not the canonical FastAPI app; not imported |
| `02-Backend/server/`, `02-Backend/routes/`, `02-Backend/database/`, `02-Backend/utils/`, `02-Backend/tests/` | 15 | A **second** backend inside `02-Backend` — Flask + SQLite (`server/app.py`, `werkzeug`) + its tests | `flask`/`werkzeug`/`flask_cors` **not in `requirements.txt`** → cannot run; `app/` imports none of it |

## Removed — root legacy entry points / scripts

| Path | What it was | Proof unused |
|---|---|---|
| `server.js`, `sever.js` | Express servers (one is a typo dup) | Not in `package.json` scripts |
| `command-system.js` | Legacy command router | No references |
| `main.py` | Flask entry | Not the canonical backend |
| `supabase_config.py` | Standalone config script | Not imported by `02-Backend/app/` |
| `start.bat` | Windows launcher for legacy stack | References removed servers |
| `dashboard.html`, `error.html` | Static pages | Referenced `../css`/`../js` (paths above repo root → broken) |

## Removed — broken / fictional deployment configs

| Path | Proof it was non-functional |
|---|---|
| `docker-compose-full.yml` | Builds `Dockerfile.api` / `Dockerfile.worker` that **do not exist**; provisions Mongo/Redis unused by the Supabase stack |
| `deployment/` (`deploy-all.sh`) | Runs `backend/server.js`, `backend/workers/*.js`, `npm run migrate`, `npm run test:smoke` — none exist; PM2/nginx for a different architecture |
| `DevOps-Deployment/` | Deployment assets for the removed stacks |
| `scripts/` | `migrate_memory_to_sqlite.py` (SQLite, not Supabase) + `setup_env.ps1` for legacy layout |

## Removed — committed junk / orphans

| Path | Reason |
|---|---|
| `logs/astravox.log` | Committed log file (now gitignored) |
| `database/database.py` | 2-line `print()` stub, never imported |
| `database/schemas/CompleteSchema.sql` | Orphan schema (users/sessions/payments/…) that conflicts with the canonical `supabase_setup.sql`; referenced nowhere |
| `02-Backend` `google-generativeai` dep | Unused dependency (no canonical code imports Gemini) — removed from `requirements.txt` |

## Kept (intentionally not removed)

- `src/`, `02-Backend/app/`, `database/schemas/supabase_setup.sql`, `database/migrations/`.
- Build/config: `index.html`, `package.json`, `package-lock.json`, `vite.config.js`, `.env.example`, `.gitignore`, `.vscode/`.
- Documentation: all root `*.md` and `Documentation/`. **Note:** several docs describe the now-removed legacy architecture and are stale — flagged in `AUDIT_REPORT.md` as recommended follow-up, but documentation was not deleted (not code / low risk).
