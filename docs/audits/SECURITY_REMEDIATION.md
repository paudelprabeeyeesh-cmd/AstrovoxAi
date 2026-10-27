# AstrovoxAI Security Remediation Plan

**Repository:** https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi  
**Status:** In Progress  
**Priority Order:** Critical → High → Medium → Low  

---

## Completed Fixes (Verified)

### P-01: Fix Pydantic forward-reference errors in backend auth
**Files:** `backend/app/auth/router.py`, `backend/app/auth/models.py`, `backend/app/workspaces/router.py`, `backend/app/workspaces/models.py`  
**Action:** Removed `from __future__ import annotations` from modules defining Pydantic models used as FastAPI route models. Added missing `EmailStr` import in `workspaces/models.py`.  
**Verification:** `import app.auth` succeeds; backend auth routes importable.  
**Status:** Complete

### P-02: Fix ESLint config rule reference
**File:** `eslint.config.js`  
**Action:** Changed `security/detect-pseudo-random-prng` → `security/detect-pseudoRandomBytes`.  
**Verification:** ESLint starts without crashing.  
**Status:** Complete

### P-03: Remove UTF-16 BOM from frontend source
**File:** `src/app.jsx`  
**Action:** Re-saved as UTF-8 without BOM.  
**Verification:** Vite/esbuild can parse `src/app.jsx`.  
**Status:** Complete

### P-04: Create mathematics module with regression tests
**Files:** `02-Backend/app/math/__init__.py`, `02-Backend/tests/math/test_math.py`  
**Action:** Created pure-Python math module (linear algebra, gradients, statistics) with 10 regression tests.  
**Verification:** 10/10 tests pass.  
**Status:** Complete

---

## In Progress / Next

### P-05: Fix frontend lint errors (71 errors)
**Files:** `eslint.config.js`, `src/**`  
**Actions:**
1. Fix `no-undef` errors: add React imports where missing (`useEffect`, `requestAnimationFrame`, `atob`, `cancelAnimationFrame`)
2. Fix `no-empty` errors: fill empty block statements or remove them
3. Fix `no-useless-escape` errors: remove unnecessary escape characters
4. Fix `no-redeclare` errors: rename duplicate variable declarations
5. Fix parsing errors: correct malformed JSX/TS syntax

**Estimated effort:** 2-4 hours  
**Verification:** `npm run lint` reports 0 errors  
**Status:** Not started

### P-06: Fix frontend typecheck errors
**Files:** `tsconfig.json`, `src/components/**/*.jsx`  
**Actions:**
1. Configure `tsconfig.json` to handle `.jsx` files properly (`allowJs`, `jsx` option)
2. Fix JSX syntax errors in `CausalChain.jsx`, `StateDiff.jsx`, `Timeline.jsx`, `OmnipotentAssistant.jsx`

**Estimated effort:** 2-3 hours  
**Verification:** `npm run typecheck` exits 0  
**Status:** Not started

### P-07: Fix frontend production build
**Files:** `vite.config.js`, `node_modules/framer-motion/`  
**Actions:**
1. Resolve framer-motion dependency resolution failure (`./utils/use-motion-value-event.mjs`)
2. Create root `index.html` entry point (already created)
3. Fix remaining source-level build errors

**Estimated effort:** 1-2 hours  
**Verification:** `npm run build` exits 0 with `dist/` output  
**Status:** Not started

### P-08: Fix backend test collection (69 errors)
**Files:** `pytest.ini`, `tests/`  
**Actions:**
1. Add `asyncio_mode = auto` to `pytest.ini` or install `pytest-asyncio`
2. Fix pre-existing test import errors (6266 tests collected, 69 collection errors)

**Estimated effort:** 1-2 hours  
**Verification:** `pytest --collect-only` reports 0 errors  
**Status:** Not started

---

## Requires Owner / Credential Action (Cannot be completed by code changes alone)

### P-09: Rotate all exposed provider API keys
**Component:** Root `.env`, Git history  
**Action:** Rotate keys through each provider's official interface:
- XAI API key
- OpenRouter API key
- OpenAI API key
- Gemini API key
- Supabase keys (URL + anon key + service role)

**Verification:** New keys work; old keys revoked  
**Status:** Pending owner action  
**Note:** Never print secret values. Document which providers need rotation only.

### P-10: Clean Git history of secrets
**Component:** `.git` directory  
**Action:** Run `git filter-repo` or BFG Repo-Cleaner to strip secrets from all commits. Force-push to remote (owner authorization required).  
**Status:** Pending owner action

### P-11: Add automated secret scanning to CI
**Component:** `.github/workflows/`  
**Action:** Add gitleaks or trufflehog step to all CI workflows.  
**Status:** Pending implementation

### P-12: Enable branch protection on `main`
**Component:** GitHub repository settings  
**Action:** Require PR reviews, require CI checks, restrict force-pushes.  
**Status:** Pending owner action

### P-13: Add dependency vulnerability scanning
**Component:** CI / Release pipeline  
**Action:** Add `npm audit` and `pip audit` to CI; generate SBoM for releases.  
**Status:** Pending implementation

---

## Regression Test Coverage

| Test File | Tests | Status |
|-----------|-------|--------|
| `02-Backend/tests/math/test_math.py` | 10 | All pass |
| `02-Backend/tests/security/test_auth_security_fixes.py` | 11 | All pass |

---

## Remediation Verification Checklist

- [ ] P-01: Pydantic forward-ref fixes — verified
- [ ] P-02: ESLint config fix — verified
- [ ] P-03: BOM removal — verified
- [ ] P-04: Math module + tests — verified
- [ ] P-05: Frontend lint (71 errors) — pending
- [ ] P-06: Frontend typecheck — pending
- [ ] P-07: Frontend production build — pending
- [ ] P-08: Backend test collection — pending
- [ ] P-09: Rotate provider keys — pending owner
- [ ] P-10: Clean Git history — pending owner
- [ ] P-11: Secret scanning in CI — pending
- [ ] P-12: Branch protection — pending owner
- [ ] P-13: Dependency scanning — pending

---

## Definition of Done

- All code-level fixes (P-01 through P-04) verified with passing tests
- Remaining findings (P-05 through P-08) tracked with clear remediation steps
- Owner-required actions (P-09 through P-13) documented with exact steps
- No secret values present in this document or any commit
