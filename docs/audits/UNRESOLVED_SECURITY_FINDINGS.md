# AstrovoxAI Unresolved Security Findings

**Repository:** https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi  
**Status:** Requires owner action / further implementation  
**Classification:** Confidential  

---

## Unresolved Findings Requiring Owner / Credential Action

### UF-01: Live provider API keys in `.env` (HIGH)

**Component:** Root `.env` (untracked), Git history  
**Description:** Live provider API keys (XAI, OpenRouter, OpenAI, Gemini, Supabase) exist in the local `.env` file and potentially in Git history.  
**Required Action:** Rotate all exposed keys through each provider's official management interface:
1. XAI — Rotate API key at x.ai developer console
2. OpenRouter — Rotate API key at openrouter.ai keys page
3. OpenAI — Rotate API key at platform.openai.com/api-keys
4. Gemini — Rotate API key at Google Cloud Console / MakerSuite
5. Supabase — Rotate keys at supabase.com dashboard → Settings → API

**Verification:** New keys function; old keys return 401/403.  
**Status:** Pending owner action  
**Constraint:** Cannot be completed by code changes; requires credential access.

---

### UF-02: Secrets exposed in Git history (HIGH)

**Component:** `.git` directory (all branches)  
**Description:** Secrets committed in historical commits remain accessible via `git log -p`, `git show`, or `git filter-repo --invert-paths`. Removing a file from HEAD does not eliminate historical exposure.  
**Required Action:**
1. Run `git log --all -p | grep -iE "(api[_-]?key|secret|token|password|sk-|ghp_)"` to audit.
2. Use `git filter-repo` or BFG Repo-Cleaner to strip secrets from all commits.
3. Force-push to remote (requires repository owner authorization).
4. Rotate all keys found in history (see UF-01).

**Status:** Pending owner action  
**Constraint:** Force-push rewrites history; requires explicit authorization.

---

### UF-03: Frontend lint errors — 71 errors (MEDIUM)

**Component:** `eslint.config.js`, `src/`  
**Description:** `npm run lint` reports 509 problems (71 errors, 438 warnings). Primary error categories:
- `no-undef`: React, `useEffect`, `requestAnimationFrame`, `atob`, `cancelAnimationFrame`, `session`
- `no-empty`: Empty block statements in multiple files
- `no-useless-escape`: Unnecessary escape characters
- `no-redeclare`: Duplicate variable declarations
- Parsing errors: Malformed JSX/TS syntax

**Required Action:** Fix lint errors incrementally, starting with `no-undef` (add missing React imports) and parsing errors.  
**Verification:** `npm run lint` exits 0 with max-warnings 0.  
**Status:** Not started  
**Estimated effort:** 2-4 hours

---

### UF-04: Frontend typecheck errors (MEDIUM)

**Component:** `tsconfig.json`, `src/components/**/*.jsx`  
**Description:** `tsc --noEmit` reports numerous errors in `.jsx` files (TS1005, TS1381, TS17008, TS2657, etc.), primarily malformed JSX syntax and missing type configuration.  
**Required Action:**
1. Configure `tsconfig.json` with `allowJs: true` and `jsx: "react-jsx"` (or `"react"`).
2. Fix JSX syntax errors in `CausalChain.jsx`, `StateDiff.jsx`, `Timeline.jsx`, `OmnipotentAssistant.jsx`, and others.

**Verification:** `npm run typecheck` exits 0.  
**Status:** Not started  
**Estimated effort:** 2-3 hours

---

### UF-05: Frontend production build failure (MEDIUM)

**Component:** `vite.config.js`, `node_modules/framer-motion/`  
**Description:** `npm run build` fails because framer-motion cannot resolve `./utils/use-motion-value-event.mjs`. Root `index.html` was created; `src/app.jsx` BOM and default export fixed; `OmnipotentAssistant.jsx` and `InfiniteScroll.jsx` syntax errors fixed.  
**Required Action:**
1. Investigate framer-motion version compatibility (reinstall or pin version).
2. Resolve any remaining entry module resolution issues.
3. Verify `dist/` output is generated.

**Verification:** `npm run build` exits 0 with production assets in `dist/`.  
**Status:** Not started  
**Estimated effort:** 1-2 hours

---

### UF-06: Backend test collection errors — 69 errors (MEDIUM)

**Component:** `pytest.ini`, `tests/`  
**Description:** `pytest --collect-only` collects 6266 tests but reports 69 collection errors. Most are `'asyncio' not found in markers` configuration errors; some are pre-existing test import errors.  
**Required Action:**
1. Install `pytest-asyncio` and add `asyncio_mode = auto` to `pytest.ini`.
2. Fix pre-existing test module import errors.
3. Run full backend test suite.

**Verification:** `pytest --collect-only` reports 0 errors; full suite passes.  
**Status:** Not started  
**Estimated effort:** 1-2 hours

---

### UF-07: No automated secret scanning in CI (MEDIUM)

**Component:** `.github/workflows/`  
**Description:** No secret scanning (gitleaks, trufflehog, detect-secrets) configured in GitHub Actions workflows.  
**Required Action:** Add a secret scanning step to CI workflows that runs on every pull request and push to `main`.  
**Verification:** CI workflow file contains a secret scanning step.  
**Status:** Not started  
**Estimated effort:** 1 hour

---

### UF-08: No branch protection on `main` (MEDIUM)

**Component:** GitHub repository settings  
**Description:** Branch protection rules are not enforced. Unreviewed or broken changes can be merged directly to `main`.  
**Required Action:** Enable branch protection on `main`:
- Require pull request reviews (minimum 1)
- Require status checks (CI must pass)
- Restrict force-pushes
- Restrict deletions

**Verification:** GitHub repository settings show branch protection enabled.  
**Status:** Pending owner action  
**Constraint:** Requires GitHub repository settings access.

---

### UF-09: No dependency vulnerability scanning (LOW)

**Component:** CI / Release pipeline  
**Description:** No `npm audit`, `pip audit`, or SBoM generation configured.  
**Required Action:**
1. Add `npm audit` and `pip audit` to CI workflows.
2. Generate SBoM (e.g., using `syft` or `cyclonedx-bom`) for releases.

**Verification:** CI workflows contain vulnerability scanning steps; SBoM artifacts exist for releases.  
**Status:** Not started  
**Estimated effort:** 1-2 hours

---

## Completed Fixes (Reference)

| Fix | File | Status |
|-----|------|--------|
| Pydantic `from __future__ import annotations` removed | `backend/app/auth/router.py`, `backend/app/auth/models.py`, `backend/app/workspaces/router.py`, `backend/app/workspaces/models.py` | Verified |
| ESLint rule name fixed | `eslint.config.js` | Verified |
| UTF-16 BOM removed | `src/app.jsx` | Verified |
| Mathematics module created | `02-Backend/app/math/__init__.py` | Verified |
| Math regression tests | `02-Backend/tests/math/test_math.py` (10 tests, all pass) | Verified |
| Security regression tests | `02-Backend/tests/security/test_security_regression.py` | Created |
| Auth security tests | `02-Backend/tests/security/test_auth_security_fixes.py` (11 tests, all pass) | Verified |

---

## Definition of Done

- [ ] All code-level fixes (CF-01 through CF-04) verified with passing tests
- [ ] UF-03 through UF-06 fixed and verified
- [ ] UF-07 through UF-09 implemented
- [ ] UF-01 and UF-02 completed by owner with credential rotation and history cleanup
- [ ] No secret values in any report or commit
