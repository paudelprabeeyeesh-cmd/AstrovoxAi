# ASTRAVOX PRIME — Repository Audit & Refactor Report

> Full-repository audit performed on the `main` branch. This report documents the
> real architecture, every issue found, what was fixed (with verification), what
> was removed (with proof it was unused), and what remains. Items that could not
> be executed/verified in this environment are explicitly marked **NOT VERIFIED**.

---

## 1. Repository Architecture (what actually runs)

The repo contains **four overlapping, mostly-disconnected stacks**. Only one path is
actually wired together and runnable:

### Active stack (the real application)
- **Frontend** — Vite + React 18, source in `src/`, entry `index.html` → `src/main.jsx` → `src/app.jsx`.
  - Components: `auth.jsx`, `Dashboard.jsx`, `Sidebar.jsx`, `Chat.jsx`, `MemoryPanel.jsx`,
    `SettingsPanel.jsx`, `telemetry.jsx`, `terminalconsole.jsx`, `ProtectedRoute.jsx`.
  - Talks **directly to Supabase** (auth, conversations, messages, realtime) via `src/supabase.js`.
  - Chat send goes to a **FastAPI** endpoint `POST /chat/message`.
- **Backend** — FastAPI app in `02-Backend/app/` (`main.py`, `auth.py`, `chat.py`, `api.py`,
  `database.py`, `memory.py`). Started via `npm run backend`
  (`uvicorn app.main:app` on port 8000). Uses Supabase (PostgreSQL) + OpenAI.
- **Database** — Supabase/PostgreSQL. Real schema: `database/schemas/supabase_setup.sql`
  (tables `profiles`, `conversations`, `messages`, `ai_memory`, `user_settings`; RLS enabled).

### Legacy / duplicate / dead (NOT part of the running app)
| Path | Status | Evidence |
|------|--------|----------|
| `server.js`, `sever.js` | Dead | Express + better-sqlite3 servers; hardcoded keyword "AI". Not referenced by frontend (which calls FastAPI / Supabase). `sever.js` is a typo'd duplicate of `server.js`. |
| `main.py` + `02-Backend/server/app.py` | Dead | A separate Flask-style `create_app()` server on port 5000; unrelated to the FastAPI app the frontend uses. |
| `supabase_config.py` | Dead | Standalone script with a placeholder key; imported by nothing. |
| `AI-Integration/`, `03-AI-Integration/`, `AI-Integration/ai-logic` vs `ai_logic` | Legacy/duplicate | Parallel Python AI modules (Gemini), not imported by the FastAPI backend. Contained the leaked key. |
| `Backend/` (vs `02-Backend/`) | Duplicate scaffold | Separate empty-ish backend tree. |
| `Frontend/`, `01-Frontend/` (vs `src/`) | Duplicate scaffold | Static HTML/CSS components, not used by the Vite app. |
| `app/`, `api/`, `ui/`, `themes/`, `voice-ai/`, `data/` | Scaffold/Kotlin | `.kt` files (Kotlin), `desktop.ini`-only folders — not part of the JS/Python app. |
| `astravox-ai/` | Separate mini-app | Its own `server.js` + `package.json` + committed `node_modules`. |
| `routes/`, `database/database.py` (root) | Duplicate | Mirror of `02-Backend/routes` / db. |
| `00-Core-Management/`, `Team-Resources/`, `Design-System/`, `Documentation/`, `Analytics/`, `Backups/` | Docs/empty | Planning docs and empty placeholder directories. |

**Conclusion:** the maintainable surface is `src/` + `02-Backend/app/` + `database/schemas/supabase_setup.sql`.
Everything else is legacy, duplicated, or scaffold. (Deletion of these large trees was **not** performed
in this pass — see §6 "Why large folders were not deleted".)

### Startup flow (active stack)
```
npm run dev        -> Vite dev server :5173 (proxies /api -> :8000, strips /api)
npm run backend    -> uvicorn app.main:app :8000 (FastAPI)
Browser            -> index.html -> main.jsx -> app.jsx
app.jsx            -> supabase.auth.getSession() -> Auth (logged out) | Dashboard (logged in)
```

### Authentication flow
```
auth.jsx -> supabase.auth.signUp / signInWithPassword / resetPasswordForEmail
         -> Supabase Auth issues JWT (access_token)
app.jsx onAuthStateChange -> renders Dashboard with session
Chat.jsx -> attaches Bearer access_token -> FastAPI validates via supabase.auth.get_user(token)
```

### AI request flow
```
Chat.jsx (POST {VITE_API_URL|/api}/chat/message, Bearer token)
  -> FastAPI /chat/message
     -> verify token (Supabase) -> save user msg -> load recent msgs + memory
     -> OpenAI chat.completions.create(model) -> save assistant msg -> update conversation
  -> returns ai_message -> rendered in Chat.jsx
```

### Database flow
```
Frontend (Supabase JS, RLS-enforced) : conversations + messages read/insert/soft-delete
Backend (Supabase service)           : conversations/messages/ai_memory/user_settings CRUD
```

---

## 2. Problem Inventory

### 🔴 Critical (P0)
1. **Leaked live secret committed** — `AI-Integration/ai-logic/.env` contained a real
   `GEMINI_API_KEY`. Present in git history → must be **rotated** (owner action).
2. **Frontend cannot build out of the box** — `vite.config.js` set `minify: 'terser'` but
   `terser` is not a dependency → `vite build` fails (`terser not found`).
3. **Case-sensitive import break** — `main.jsx` imported `./App.jsx` while the tracked file is
   `src/app.jsx`. Works on Windows/macOS (case-insensitive) but **breaks builds on Linux**
   (CI, Vercel, Netlify, Docker).
4. **Repo hygiene / leaked artifacts** — 326 Windows `desktop.ini` files, 28 `.pyc` files,
   committed SQLite `.db` files, and editor backup/junk files tracked in git.

### 🟠 High (P1)
5. **Hardcoded backend URL** — `Chat.jsx` fetched `http://localhost:8000/chat/message`
   (ignored `VITE_API_URL`, broke in any non-local deployment).
6. **Unsafe CORS** — FastAPI used `allow_origins=["*"]` **with** `allow_credentials=True`
   (rejected by browsers; also overly permissive).
7. **DB: signup trigger disabled** — `supabase_setup.sql` defines `handle_new_user()` but the
   `on_auth_user_created` trigger is commented out → new users get no `profiles` / `user_settings`
   row, which can break `/api/me`, `/api/stats`, and settings.
8. **DB: no indexes** — no indexes on `conversations.user_id`, `messages.conversation_id`,
   `ai_memory.user_id`, etc. → full scans as data grows.

### 🟡 Medium (P2)
9. **Per-request Supabase client** — `chat.py` and `api.py` re-create a Supabase client on
   **every request** inside `get_user_id_from_token` (duplicated code + repeated init).
10. **Backend import structure** — `app/main.py` uses absolute imports (`from auth import ...`)
    instead of package-relative (`from .auth import ...`); fragile depending on CWD. *(static finding)*
11. **Deprecated API** — `datetime.utcnow()` used in `main.py`/`api.py` (deprecated in Py 3.12+).
12. **Dependency advisory** — `esbuild`/`vite` dev-server advisory `GHSA-67mh-4wv8-2f99`
    (dev-only; fix requires a Vite major bump — deferred as breaking).
13. **Four parallel backends / duplicate folders** — large maintenance/confusion surface.

### 🟢 Low (P3)
14. Inline styles everywhere (no shared styling system); duplicated spinner markup.
15. No automated tests run / no CI workflow (`.github/` absent).
16. README "Project Structure" doesn't match the real tree.
17. `start.bat` hardcodes a personal path `G:\My Drive\...`.

---

## 3. Prioritized Roadmap
- **P0 (fixed this pass):** rotate leaked key (owner), make build succeed, fix case import, purge junk + harden `.gitignore`.
- **P1 (fixed this pass):** env-driven API URL, safe CORS, DB migration for trigger + indexes.
- **P2 (recommended next):** singleton Supabase client + shared auth dependency, package-relative imports, replace `utcnow()`, plan Vite upgrade.
- **P3 (backlog):** consolidate to the single active stack and delete legacy trees, add CI + tests, shared styles, fix docs.

---

## 4. Changes Made (with verification)

| # | Change | File(s) | Verification |
|---|--------|---------|--------------|
| 1 | `minify: 'terser'` → `'esbuild'` | `vite.config.js` | ✅ `npm run build` succeeds |
| 2 | Import `./App.jsx` → `./app.jsx` | `src/main.jsx` | ✅ build resolves on case-sensitive FS |
| 3 | Escape literal `>>` JSX text | `src/auth.jsx` | ✅ build emits **no** esbuild warnings |
| 4 | API URL via `VITE_API_URL \|\| '/api'` | `src/Chat.jsx` | ✅ build succeeds |
| 5 | Env-driven, credential-safe CORS | `02-Backend/app/main.py` | ✅ `python -m py_compile` passes |
| 6 | Harden ignore rules | `.gitignore` | ✅ verified ignores `.env`, `__pycache__`, `*.db`, `desktop.ini` |
| 7 | Document `ALLOWED_ORIGINS` | `.env.example` | n/a (docs) |
| 8 | Additive indexes + signup trigger | `database/migrations/0001_indexes_and_signup_trigger.sql` | ⚠️ **NOT VERIFIED** at runtime (no DB creds); SQL syntax-reviewed, idempotent |

**Build result (after fixes):** `✓ 81 modules transformed … ✓ built in ~1s`, exit 0, no warnings.
**Backend:** `py_compile` of all `02-Backend/app/*.py` passes. Full runtime is **NOT VERIFIED**
(requires Supabase + OpenAI credentials and dependency install).

---

## 5. Files Removed (with proof of non-use)

All removals are provably-junk or generated artifacts — **no source code was deleted.**
- **326 `desktop.ini`** — Windows folder-metadata. Proof: `grep` across all `.js/.jsx/.py/.json/.html/.yml/.sh` found **zero** references.
- **28 `*.pyc` + `__pycache__/`** — Python bytecode (regenerated from source). Now git-ignored.
- **`02-Backend/database/chat.db`, `AI-Integration/ai_logic/memory.db`** — local SQLite artifacts; not referenced; the active stack uses Supabase.
- **`AI-Integration/ai-logic/.env`** — leaked-secret file (must not be tracked).
- **Stray junk:** `first.txt` ("AstrovoxAi"), `test.txt` (binary garbage), `README_REAL.md`,
  `README.md~efdbe4…` (editor backup), `02-Backend/server/app_test.txt`, `start-app.bat` (0 bytes).

Tracked file count: **737 → 374**.

---

## 6. Why large legacy folders were NOT deleted
The prompt requires proving a file is unreferenced before deletion. The duplicate/legacy trees
(`Backend/`, `Frontend/`, `01-Frontend/`, `AI-Integration/`, `app/`, `api/`, `ui/`, `themes/`,
`voice-ai/`, `astravox-ai/`, root `routes/`, etc.) are large and cross-referenced internally; proving
each tree fully dead is high-risk in a single pass and could destroy work-in-progress. They are
**documented as legacy candidates** here and left in place for a deliberate, reviewed cleanup PR.

---

## 7. Remaining Issues / NOT VERIFIED
- **Leaked Gemini key rotation** — owner action; key is compromised regardless of file removal.
- **Backend runtime** — start, request handling, OpenAI calls: **NOT VERIFIED** (no creds/deps).
- **DB migration execution** — **NOT VERIFIED** (no Supabase access); SQL is idempotent & reviewed.
- **P2 items** (singleton client, relative imports, `utcnow()`, Vite upgrade) — not changed this pass.
- **Legacy-stack consolidation** — deferred (see §6).
- **No CI** — `.github/` absent, so "verify CI passes" is **NOT VERIFIED / N/A**.

---

## 8. Scores
- **Production readiness: 3/10** — active stack now builds and has safer CORS/secrets/DB migration,
  but backend is unverified, secrets were leaked, no CI/tests, and four competing stacks remain.
- **Technical debt: 8.5/10 (very high)** — ~50% of tracked files were junk; multiple dead backends;
  no tests/CI; docs mismatch reality.

## 9. Recommended future improvements
1. Rotate the leaked key; scrub git history (e.g. `git filter-repo`) if the repo is/was public.
2. Pick the single active stack and delete the legacy trees in a reviewed PR.
3. Add CI (`.github/workflows`): `npm ci && npm run build`, backend `py_compile`/`pytest`, secret scanning.
4. Backend: one shared Supabase client singleton + a FastAPI auth dependency; package-relative imports.
5. Apply the DB migration; add the OpenAI/model config as env-driven (currently hardcoded `gpt-4`).
6. Replace inline styles with a shared system; add error boundaries and loading skeletons.
