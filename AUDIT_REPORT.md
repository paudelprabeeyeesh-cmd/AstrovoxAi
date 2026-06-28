# AUDIT REPORT — AstroVoxAI

_Production-readiness audit & refactor. Builds on PR #2 (build/CORS/secret/junk fixes)._

This pass: fixed the backend startup blocker, removed duplicate per-request DB
clients and duplicated auth code, fixed a memory bug, removed 337 files of
proven-unused legacy code, added tests, and made the backend lint-clean.

---

## 1. Architecture

### Canonical stack (the only one that runs)
```
Browser
  │
  ▼
index.html ──► /src/main.jsx ──► src/app.jsx (React, Vite)
  │                                  │
  │  Supabase JS (auth, data, RLS)   │  fetch ${VITE_API_URL|/api}/chat/message
  ▼                                  ▼
Supabase  ◄───────────────  FastAPI  02-Backend/app/main.py
(Postgres + Auth + RLS)      ├─ auth.py    (/auth/*)
                             ├─ chat.py    (/chat/*)  ──► OpenAI
                             ├─ api.py     (/api/*)
                             ├─ memory.py  (/memory/*)
                             ├─ supabase_client.py  (singleton)
                             └─ auth_utils.py        (shared token check)
```

### Dependency map (canonical)
- **Frontend** `src/`: `main.jsx → app.jsx → {auth, Chat, Dashboard, Sidebar,
  MemoryPanel, SettingsPanel, ProtectedRoute, telemetry, terminalconsole}`;
  `supabase.js` (Supabase client from `import.meta.env`). Backend touched only by
  `Chat.jsx` via `import.meta.env.VITE_API_URL || '/api'`.
- **Backend** `02-Backend/app/`: `main.py` includes 4 routers; routers import
  `database.py` (data) + `auth_utils.py` (auth); both `database.py` and `auth.py`
  use the `supabase_client.get_supabase()` singleton. External: `fastapi`,
  `uvicorn`, `pydantic`, `supabase`, `openai`, `python-dotenv`.
- **DB**: `database/schemas/supabase_setup.sql` (canonical) + idempotent
  `database/migrations/0001_indexes_and_signup_trigger.sql`.

### Startup flow
- Frontend: `npm run dev`/`npm run build` (Vite). Entry `index.html → /src/main.jsx`.
- Backend: `npm run backend` → `cd 02-Backend && uvicorn app.main:app`. Requires
  `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` (client built at import);
  `OPENAI_API_KEY` for chat; `ALLOWED_ORIGINS` for CORS.

### Auth flow
Supabase signup/login (frontend) → JWT → sent as `Authorization: Bearer` →
`auth_utils.get_user_id_from_token` validates via `supabase.auth.get_user` →
RLS policies enforce per-user row access.

---

## 2. Issues found & status

### P0 — Critical
| # | Issue | Status |
|---|---|---|
| 1 | Frontend build broken (`minify:'terser'`, terser not installed) | ✅ Fixed in PR #2 (esbuild) |
| 2 | Case-sensitive import `./App.jsx` vs `src/app.jsx` (breaks Linux/CI) | ✅ Fixed in PR #2 |
| 3 | **Backend cannot start** — top-level imports fail under `uvicorn app.main:app` | ✅ Fixed (package-relative imports + `__init__.py`); boot verified |
| 4 | Live Gemini API key committed (`AI-Integration/ai-logic/.env`) | ⚠️ File untracked (PR #2); **key still in git history — OWNER MUST ROTATE** |

### P1 — High
| # | Issue | Status |
|---|---|---|
| 5 | Hardcoded `http://localhost:8000` in `Chat.jsx` | ✅ Fixed in PR #2 (env-driven) |
| 6 | Unsafe CORS (`*` + credentials, all methods/headers) | ✅ Fixed in PR #2 (env origins, restricted methods/headers) |
| 7 | New Supabase client created **per request** (auth helper) ×3 | ✅ Fixed (singleton `get_supabase()`) |
| 8 | User memory built but never sent to OpenAI | ✅ Fixed (prepended as system message) |
| 9 | Missing indexes + signup trigger commented out (new users get no profile/settings) | ✅ Migration added; **execution NOT VERIFIED** (no creds) |

### P2 — Medium
| # | Issue | Status |
|---|---|---|
| 10 | `get_user_id_from_token` duplicated in 3 files | ✅ Centralized in `auth_utils.py` |
| 11 | `datetime.utcnow()` deprecated | ✅ Replaced with `datetime.now(timezone.utc)` |
| 12 | Lint errors (unused imports/vars, formatting) | ✅ flake8-clean + black |
| 13 | No tests | ✅ Added smoke suite (5 passing) |
| 14 | Unused `google-generativeai` dependency | ✅ Removed |
| 15 | Massive legacy/duplicate trees (4+ parallel stacks) | ✅ Removed 337 proven-unused files |

### P3 — Low / remaining
| # | Issue | Status |
|---|---|---|
| 16 | No frontend JS linter (no ESLint config) | ⏳ Recommended; `vite build` is the current gate |
| 17 | Docs (`README`, etc.) describe removed legacy stack | ✅ `README` rewritten; `DEPLOYMENT.md` added (other legacy `.md`s still recommend rewrite) |
| 18 | No CI/CD (`.github/workflows` absent) | ✅ Added `ci.yml` (build + flake8 + pytest + gitleaks) |
| 19 | No rate limiting on auth/chat endpoints | ✅ Added `slowapi` per-IP limiter (all endpoints) |
| 20 | Vite/esbuild **dev-server** advisory | ⏳ Deferred — fix needs Vite 5→8 which breaks the build (verified) |
| 21 | `print()` error logging; no input length validation | ✅ Structured logging + pydantic `Field` constraints |

---

## 3. Changes made (this pass)

See `CHANGELOG.md` for the itemized list and `CLEANUP_REPORT.md` for removals.

Backend refactor (commit `d0e88a5`): relative imports, `supabase_client.py`
singleton, `auth_utils.py` shared dep, `datetime` fix.
Cleanup (commit `9ffb1b8`): 321 files.
Quality (commit `48cfcbd`): flake8/black, memory bug, dead Flask layer + stub +
orphan schema removed, smoke tests.

---

## 4. Database

- Schema `supabase_setup.sql`: 5 tables (`profiles`, `conversations`, `messages`,
  `ai_memory`, `user_settings`), RLS enabled on all, per-user policies, and
  `handle_new_user()` — but its trigger was **commented out**.
- Migration `0001` (idempotent): adds 5 indexes on hot query paths
  (`conversations(user_id)`, `(user_id, updated_at DESC)`,
  `messages(conversation_id, created_at)`, `messages(user_id)`,
  `ai_memory(user_id, importance DESC, created_at DESC)`) and **wires the signup
  trigger** with `ON CONFLICT DO NOTHING` + `DROP TRIGGER IF EXISTS`.
- Removed orphan `CompleteSchema.sql` (conflicting, unreferenced).
- **NOT VERIFIED**: execution against a live Supabase DB (no credentials here).
  SQL is idempotent and syntax-reviewed.

---

## 5. Verification

| Check | Result |
|---|---|
| `npm run build` | ✅ 81 modules, exit 0 |
| `python -m flake8 app tests` | ✅ clean |
| `python -m pytest -q` | ✅ 9 passed |
| `uvicorn app.main:app` boot + curl `/health*`, `/`, `/api/me` (401), `/docs` | ✅ |
| `python -m py_compile app/*.py` | ✅ |
| `docker build` (new `02-Backend/Dockerfile`) | ❌ NOT VERIFIED (no Docker in env) |
| DB migration on live Supabase | ❌ NOT VERIFIED (no creds) |
| Full chat flow (login → message → OpenAI) | ❌ NOT VERIFIED (no Supabase/OpenAI creds) |

---

## 6. Recommended future improvements
1. **Rotate the leaked Gemini key** and scrub git history (`git filter-repo`) — blocking security item; only the owner can do this.
2. Run the migration against a live/staging Supabase to confirm indexes + signup trigger, then smoke-test the full login → chat flow.
3. Add ESLint + a frontend `lint` script (the only remaining P3 code item).
4. Plan a deliberate Vite 5 → 7/8 upgrade PR to clear the dev-server esbuild advisory (it breaks the current build, so it needs dedicated work).
5. Rewrite or remove the remaining stale `.md` docs (`Architecture.md`, `API.md`, `SETUP.md`, etc.) that still reference the removed legacy stack.

---

## 7. Scores

| Metric | Before (start of pass) | After |
|---|---|---|
| Production readiness | 3 / 10 | **8 / 10** (backend boots, builds clean, 9 tests pass, CI + rate limiting + structured logging + input validation + Docker + docs; held below 9.5 only by owner key rotation and live DB/chat verification) |
| Technical debt | 8.5 / 10 (high) | **2.5 / 10** (one canonical stack, 374→44 files, lint-clean, tested, CI-gated) |
