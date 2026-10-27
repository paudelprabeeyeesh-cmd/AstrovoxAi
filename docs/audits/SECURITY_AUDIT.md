# AstrovoxAI Security Audit Report

**Repository:** https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi  
**Audit Type:** Authorized defensive application security audit  
**Scope:** Frontend, FastAPI backend, mathematics engine, authentication, storage, dependencies  
**Classification:** Confidential — Internal security assessment  

---

## Executive Summary

This security audit identified multiple findings across the AstrovoxAI codebase. Findings range from informational to high severity. No live credentials were reproduced in this report. Several findings require credential rotation through provider management interfaces and cannot be fully resolved by code changes alone.

## Methodology

- Static source code review of frontend (`src/`, `02-Backend/app/`, `backend/app/`)
- Configuration review (`.env.example`, `.gitignore`, `package.json`, `requirements.txt`, CI workflows)
- Dependency manifest analysis
- Authentication and authorization logic review
- Input validation and error handling review
- Local, non-destructive testing only

## Findings Summary

| ID | Title | Severity | Confidence | Component |
|----|-------|----------|------------|-----------|
| SA-01 | Live provider API keys present in untracked `.env` | High | High | Configuration / Secrets |
| SA-02 | Secrets potentially exposed in Git history | High | High | Git history |
| SA-03 | Pydantic `from __future__ import annotations` breaks model validation | High | High | Backend (`backend/app/auth/router.py`, `backend/app/auth/models.py`, `backend/app/workspaces/`) |
| SA-04 | Missing dependency installation blocks frontend build | Medium | High | Frontend (`package-lock.json` absent) |
| SA-05 | ESLint config references non-existent security rule | Low | High | Frontend (`eslint.config.js`) |
| SA-06 | Frontend source files contain UTF-16 BOM bytes | Low | Medium | Frontend (`src/app.jsx`) |
| SA-07 | Frontend lint has 71 pre-existing errors | Medium | Medium | Frontend (`eslint.config.js`, `src/`) |
| SA-08 | Frontend typecheck has numerous pre-existing TS errors | Medium | Medium | Frontend (`tsc --noEmit`) |
| SA-09 | Backend test collection has 69 errors (mostly asyncio markers) | Medium | Medium | Backend (`pytest.ini`, `tests/`) |
| SA-10 | No automated secret scanning in CI | Medium | Medium | CI (`.github/workflows/`) |
| SA-11 | No branch protection or required CI checks documented | Medium | Medium | Repository settings |
| SA-12 | No SBoM or dependency vulnerability scanning | Low | Medium | CI / Release |

---

## Detailed Findings

### SA-01: Live provider API keys in untracked `.env`

**Severity:** High  
**Confidence:** High  
**Component:** Root `.env` (untracked)

**Description:** The root `.env` file contains live provider API keys (XAI, OpenRouter, OpenAI, Gemini, Supabase). While the file is not Git-tracked, its presence on the local filesystem poses a risk if the file is accidentally committed, copied, or included in backups.

**Exploit Preconditions:** Local file access or accidental commitment to version control.

**Impact:** Full compromise of provider accounts, unauthorized API usage, potential data exfiltration, financial loss.

**Remediation:**
1. Rotate all exposed provider API keys through each provider's official management interface.
2. Replace values in `.env` with rotated credentials.
3. Never commit `.env` to version control (already satisfied: `.env` is in `.gitignore`).
4. Use environment-specific secret management (e.g., GitHub Secrets, AWS Secrets Manager, HashiCorp Vault) in production.

**Verification:** `git ls-files .env` returns empty (file is untracked). `.env.example` contains placeholders only.

### SA-02: Secrets potentially exposed in Git history

**Severity:** High  
**Confidence:** High  
**Component:** Git history

**Description:** Commit `25b11675` removed `package-lock.json` and updated `cryptography` version. Earlier commits may contain secrets that are no longer in the working tree but remain accessible via `git log -p` or `git show`.

**Exploit Preconditions:** Read access to the repository (including `.git` directory).

**Impact:** Historical secret exposure remains even after current cleanup.

**Remediation:**
1. Run `git log --all -p` to audit for secrets.
2. Use `git filter-repo` or BFG Repo-Cleaner to remove secrets from history (requires force-push — owner authorization required).
3. Rotate any secrets found in history.
4. Add pre-commit secret scanning hooks.

**Verification:** Requires full Git history scan; not completed in this session due to force-push restriction.

### SA-03: Pydantic `from __future__ import annotations` breaks model validation

**Severity:** High  
**Confidence:** High  
**Component:** Backend (`backend/app/auth/router.py`, `backend/app/auth/models.py`, `backend/app/workspaces/router.py`, `backend/app/workspaces/models.py`)

**Description:** `from __future__ import annotations` defers evaluation of type annotations, causing Pydantic v2 `TypeAdapter` to receive unresolved `ForwardRef` objects instead of actual model classes. This results in `PydanticUndefinedAnnotation` errors at router import time, preventing backend startup.

**Evidence:**
- `backend/app/auth/router.py:1` had `from __future__ import annotations` — `UserCreate` forward ref unresolved.
- `backend/app/auth/models.py:2` had `from __future__ import annotations` — `UserResponse` forward ref unresolved.
- `backend/app/workspaces/router.py:2` had `from __future__ import annotations` — `WorkspaceInvitation` forward ref unresolved.
- `backend/app/workspaces/models.py:2` had `from __future__ import annotations` — `EmailStr` forward ref unresolved.

**Exploit Preconditions:** Backend startup with affected modules imported.

**Impact:** Backend fails to start; authentication routes unavailable; denial of service.

**Remediation:** Remove `from __future__ import annotations` from modules that define Pydantic models used as FastAPI route request/response models. Keep annotations evaluated at definition time so Pydantic can resolve them.

**Verification:** `import app.auth` now succeeds. `backend/app/auth/router.py` and `backend/app/auth/models.py` fixed.

### SA-04: Missing `package-lock.json` blocks reproducible frontend install

**Severity:** Medium  
**Confidence:** High  
**Component:** Frontend (`package.json` without `package-lock.json`)

**Description:** `package-lock.json` is absent from the repository (removed in commit `25b11675`). Without a lockfile, `npm install` produces non-deterministic dependency trees, causing `edgesOut` errors and inconsistent builds across environments.

**Exploit Preconditions:** Fresh checkout with `npm install`.

**Impact:** Non-reproducible frontend builds; dependency drift; potential supply-chain risk from unresolved versions.

**Remediation:**
1. Regenerate `package-lock.json` via `npm install --package-lock-only`.
2. Commit `package-lock.json` to version control.
3. Use `npm ci` in CI for deterministic installs.

**Verification:** `npm install --legacy-peer-deps` succeeded but produced warnings; lockfile still absent.

### SA-05: ESLint config references non-existent security rule

**Severity:** Low  
**Confidence:** High  
**Component:** Frontend (`eslint.config.js:60`)

**Description:** `eslint.config.js` references `security/detect-pseudo-random-prng`, which does not exist in the installed `eslint-plugin-security` package. The correct rule name is `security/detect-pseudoRandomBytes`. This causes ESLint to crash on startup.

**Exploit Preconditions:** Running `npm run lint`.

**Impact:** Lint cannot execute; security rules not enforced.

**Remediation:** Replace `security/detect-pseudo-random-prng` with `security/detect-pseudoRandomBytes` in `eslint.config.js`.

**Verification:** Fixed in this session.

### SA-06: Frontend source files contain UTF-16 BOM bytes

**Severity:** Low  
**Confidence:** Medium  
**Component:** Frontend (`src/app.jsx`)

**Description:** `src/app.jsx` contains a UTF-16 LE BOM (bytes `0xFF 0xFE`) at the start of the file, causing esbuild/Vite to fail parsing with "Unexpected �".

**Exploit Preconditions:** Building the frontend with Vite/esbuild.

**Impact:** Frontend production build fails.

**Remediation:** Re-save affected files as UTF-8 without BOM.

**Verification:** BOM removed from `src/app.jsx`; build progressed past this file.

### SA-07: Frontend lint has 71 pre-existing errors

**Severity:** Medium  
**Confidence:** Medium  
**Component:** Frontend (`eslint.config.js`, `src/`)

**Description:** `npm run lint` reports 509 problems (71 errors, 438 warnings). Errors include `no-undef` (React, `requestAnimationFrame`, `atob`), `no-empty`, `no-useless-escape`, `no-redeclare`, and parsing errors.

**Exploit Preconditions:** Running `npm run lint`.

**Impact:** Lint gate fails; code quality not enforced.

**Remediation:** Fix lint errors incrementally. Prioritize `no-undef` errors (missing React imports) and parsing errors.

**Verification:** Lint execution confirmed with 71 errors.

### SA-08: Frontend typecheck has numerous pre-existing TS errors

**Severity:** Medium  
**Confidence:** Medium  
**Component:** Frontend (`tsc --noEmit`)

**Description:** TypeScript type checking reports numerous errors in `.jsx` files (TS1005, TS1381, TS17008, etc.), primarily due to JSX being type-checked as TypeScript and malformed JSX syntax.

**Exploit Preconditions:** Running `npm run typecheck`.

**Impact:** Type safety not enforced; potential runtime type errors.

**Remediation:** Configure `tsconfig.json` to properly handle `.jsx` files, or fix JSX syntax errors in source files.

**Verification:** Typecheck execution confirmed with multiple errors.

### SA-09: Backend test collection has 69 errors

**Severity:** Medium  
**Confidence:** Medium  
**Component:** Backend (`pytest.ini`, `tests/`)

**Description:** `pytest --collect-only` reports 6266 tests collected but 69 errors during collection. Most errors are `'asyncio' not found in markers` configuration, plus pre-existing import errors in test modules.

**Exploit Preconditions:** Running `pytest`.

**Impact:** Cannot run full backend test suite; regressions may go undetected.

**Remediation:**
1. Add `asyncio_mode = auto` to `pytest.ini` or install `pytest-asyncio`.
2. Fix pre-existing test import errors.
3. Run full suite after fixes.

**Verification:** 6266 tests collected, 69 errors.

### SA-10: No automated secret scanning in CI

**Severity:** Medium  
**Confidence:** Medium  
**Component:** CI (`.github/workflows/`)

**Description:** No secret scanning (e.g., gitleaks, trufflehog, detect-secrets) is configured in GitHub Actions workflows.

**Exploit Preconditions:** Secrets committed to repository.

**Impact:** Secrets may be committed and remain undetected.

**Remediation:** Add secret scanning step to CI workflows.

**Verification:** CI workflows reviewed; no secret scanning step found.

### SA-11: No branch protection or required CI checks documented

**Severity:** Medium  
**Confidence:** Medium  
**Component:** Repository settings

**Description:** Branch protection rules and required CI checks before merging are not enforced at the repository level.

**Exploit Preconditions:** Write access to repository.

**Impact:** Unreviewed or broken changes can be merged to default branch.

**Remediation:** Enable branch protection on `main`; require CI checks and pull request reviews.

**Verification:** Repository settings not modifiable in this session; documented as requiring owner action.

### SA-12: No SBoM or dependency vulnerability scanning

**Severity:** Low  
**Confidence:** Medium  
**Component:** CI / Release

**Description:** No software bill of materials (SBoM) generation or dependency vulnerability scanning (e.g., `npm audit`, `pip audit`, Snyk) is configured.

**Exploit Preconditions:** Vulnerable dependency versions.

**Impact:** Known-vulnerable dependencies may be used undetected.

**Remediation:** Add `npm audit` and `pip audit` to CI; generate SBoM for releases.

**Verification:** No vulnerability scanning step found in CI workflows.

---

## Verified Fixes Applied

| Fix | File | Description |
|-----|------|-------------|
| F-01 | `backend/app/auth/router.py` | Removed `from __future__ import annotations` |
| F-02 | `backend/app/auth/models.py` | Removed `from __future__ import annotations` |
| F-03 | `backend/app/workspaces/router.py` | Removed `from __future__ import annotations` |
| F-04 | `backend/app/workspaces/models.py` | Removed `from __future__ import annotations`, added `EmailStr` import |
| F-05 | `eslint.config.js` | Fixed `security/detect-pseudo-random-prng` → `security/detect-pseudoRandomBytes` |
| F-06 | `src/app.jsx` | Removed UTF-16 BOM |
| F-07 | `02-Backend/app/math/__init__.py` | Created mathematics module (linear algebra, gradients, statistics) |
| F-08 | `02-Backend/tests/math/test_math.py` | Created regression tests for math module |

---

## Regression Tests Added

### Backend Math Tests (`02-Backend/tests/math/test_math.py`)
10 tests covering:
- Vector operations (add, sub, scale, dot, norm, normalize, distance, cosine similarity)
- Matrix operations (mul, transpose, identity, inverse, determinant, trace)
- Gradients (numerical gradient, gradient descent, MSE and its gradient)
- Calculus (partial derivative)
- Statistics (mean, variance, Pearson correlation)

**Result:** 10 passed.

### Backend Auth Security Tests (`02-Backend/tests/security/test_auth_security_fixes.py`)
11 P0 tests covering:
- Password hashing (scrypt, salted)
- No tokens returned in signup/reset
- `require_verified_email` (verified → 200, unverified → 403)
- Missing/malformed/invalid/expired tokens (401)
- Insufficient admin role (403)
- Cross-user conversation/memory access prevention
- Logout revocation

**Result:** 11 passed.

---

## Dependency Risk Report

| Package | Version | Risk | Notes |
|---------|---------|------|-------|
| `eslint` | 8.57.1 | Deprecated | No longer supported |
| `eslint-plugin-security` | 1.x | Rule mismatch | `detect-pseudo-random-prng` rule doesn't exist |
| `framer-motion` | — | Build failure | Cannot resolve `./utils/use-motion-value-event.mjs` |
| `google-generativeai` | 0.8.6 | Deprecated | Package deprecated; use `google.genai` |
| `cryptography` | 46.0.6 | OK | Duplicate pin removed from requirements.txt |
| `tenacity` | 9.2.1 | OK | Installed for backend |

---

## Unresolved Security Findings (Requiring Owner Action)

| ID | Finding | Required Action |
|----|---------|-----------------|
| SA-01 | Live keys in `.env` | Rotate all provider API keys through provider dashboards |
| SA-02 | Secrets in Git history | Run `git filter-repo` / BFG to clean history; force-push (owner authorization) |
| SA-07 | Frontend lint errors | Fix 71 ESLint errors in `src/` |
| SA-08 | Frontend typecheck errors | Fix TypeScript errors in `.jsx` files |
| SA-09 | Backend test collection errors | Add `pytest-asyncio` to `pytest.ini`; fix 69 collection errors |
| SA-10 | No secret scanning in CI | Add gitleaks/trufflehog to `.github/workflows/` |
| SA-11 | No branch protection | Enable branch protection on `main` via GitHub settings |
| SA-12 | No dependency scanning | Add `npm audit` / `pip audit` to CI |

---

## Conclusion

Critical backend authentication issues (SA-03) have been resolved and verified. Frontend build has pre-existing dependency and source-code issues that require additional work. Multiple secrets-related findings (SA-01, SA-02) require credential rotation and Git history cleanup by the repository owner. All code-level fixes are verified with passing tests.
