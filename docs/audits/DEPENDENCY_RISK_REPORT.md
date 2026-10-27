# AstrovoxAI Dependency Risk Report

**Repository:** https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi  
**Generated:** 2026-10-27  
**Scope:** Frontend (`package.json`), Backend (`02-Backend/requirements.txt`)

---

## Frontend Dependencies

### Declared vs Installed

| Package | Declared Version | Installed | Engine Constraint | Risk |
|---------|-----------------|-----------|-------------------|------|
| `react` | — | — | — | Not visible in lockfile (absent) |
| `vite` | 6.4.5 | 6.4.5 | — | Active |
| `eslint` | 8.57.1 | 8.57.1 | — | Deprecated (no longer supported) |
| `eslint-plugin-security` | — | 1.x | — | Rule name mismatch (config references non-existent rule) |
| `framer-motion` | — | — | — | Build failure: cannot resolve `./utils/use-motion-value-event.mjs` |
| `@supabase/supabase-js` | — | 2.118.0 | node >=22 | Engine mismatch (current node: v20.11.0) |
| `@supabase/storage-js` | — | 2.118.0 | node >=22 | Engine mismatch (current node: v20.11.0) |
| `eslint-visitor-keys` | — | 5.0.1 | ^20.19.0 || ^22.13.0 || >=24 | Engine mismatch |

### Issues Identified

1. **No `package-lock.json`:** Removed in commit `25b11675`. Non-deterministic installs; `npm install` produced `edgesOut` error initially.
2. **Deprecated ESLint:** `eslint@8.57.1` is no longer supported.
3. **Engine mismatches:** Multiple packages require Node >=22, but environment has Node v20.11.0.
4. **Framer-motion build failure:** Dependency resolution failure blocks production build.
5. **ESLint plugin rule mismatch:** Config references `detect-pseudo-random-prng` which doesn't exist (fixed to `detect-pseudoRandomBytes`).

### Recommendations

1. Regenerate and commit `package-lock.json`; use `npm ci` in CI.
2. Upgrade ESLint to a supported version (v9+).
3. Align Node.js version with package engine requirements (>=22).
4. Investigate framer-motion version compatibility.
5. Run `npm audit` to check for known vulnerabilities.

---

## Backend Dependencies

### Declared (`02-Backend/requirements.txt`)

| Package | Version | Status | Notes |
|---------|---------|--------|-------|
| `fastapi` | — | Installed | Core framework |
| `pydantic` | — | Installed | v2.x; forward-ref issues resolved |
| `sqlalchemy` | — | Installed | Added during this session |
| `pytest` | — | Installed | Test runner |
| `pytest-timeout` | — | Installed | Test timeout |
| `google-generativeai` | >=0.8.0 | Installed (0.8.6) | **Deprecated** — use `google.genai` |
| `tenacity` | — | Installed | Retry library |
| `whisper` | — | Missing | Import attempted but not installed |
| `cryptography` | 46.0.6 | Installed | Duplicate pin (43.0.3) removed |

### Issues Identified

1. **Deprecated `google-generativeai`:** Package is deprecated; migration to `google.genai` recommended.
2. **Missing `whisper`:** `app/adapters/` attempts to import whisper but it's not installed.
3. **Duplicate `cryptography` pin:** Was `43.0.3` and `46.0.6`; resolved to `46.0.6`.

### Recommendations

1. Migrate from `google-generativeai` to `google.genai`.
2. Install `whisper` or remove the import if the feature is unused.
3. Run `pip audit` to check for known vulnerabilities.
4. Pin all dependencies with exact versions for reproducibility.

---

## Supply Chain Recommendations

1. Add `npm audit` and `pip audit` to CI workflows.
2. Generate Software Bill of Materials (SBoM) for all releases.
3. Pin CI actions to immutable references (commit SHAs).
4. Use least-privilege permissions for workflow jobs.
5. Add Dependabot or similar for automated dependency updates.
