# Status

One authoritative status file. Counts here are **measured**, not reported.

Last measured: 2026-10-14 · Commit `0b703489` · Python 3.14.5
Baseline detail: [BASELINE.md](BASELINE.md)

---

## Suite health

```
python -m pytest tests -q --no-header --timeout=90 --timeout-method=thread -p no:cacheprovider
```

| Metric | Value |
|---|---|
| Tests collected | 6740 |
| Passed | 6333 |
| Failed | 393 |
| Errors | 29 |
| Skipped | 2 |
| Duration | 649.66s (0:10:49) |
| **Security & integration suites** | **0 failures** |
| Endpoint audit findings | 628 (see below) |

The suite **terminates reliably**. It previously hung, which meant it could not be used as a gate
at all — a suite that never finishes cannot fail a build.

### Collection is no longer broken

`tests/security`, `tests/services` and `tests/storage` were excluded from the default run by
`pytest.ini`'s `norecursedirs`. This was the single most consequential finding: the security suite
was never run by `python -m pytest tests`, so the only evidence it passed was a manual invocation
nobody runs in CI. They are collected now and green.

---

## Security findings — remediation state

| # | Finding | Severity | State |
|---|---|---|---|
| 1 | Passwords hashed with unsalted SHA-256 | Critical | **Fixed** — salted scrypt, legacy records verify and transparently rehash |
| 2 | Signup returned `verification_token` / `magic_link_token` | Critical | **Fixed** — tokens removed from responses; stored hashed; expiry + one-time use |
| 3 | `require_verified_email` never checked verification status | Critical | **Fixed** — rejects unverified with 403; also honours logout revocation |
| 4 | `uuid.uuid4()` / `datetime.now()` referenced without the imports | Critical | **Fixed** — imports corrected; signup and reset covered by endpoint-level tests |
| 5 | Logout did not revoke the session server-side | Critical | **Fixed** — logout requires credentials and revokes; revoked token is rejected |
| 6 | `get_db().__enter__()` never exited — connections leaked | High | **Fixed** — 12 sites across 6 modules; rollback/cleanup/concurrency tested |
| 7 | Coverage gate compared the threshold to itself | High | **Verified fixed** — parses real coverage XML; fails on missing/unparseable/empty data |
| 8 | Privileged endpoints not audited | High | **Audited** — 628 findings, remediation not started |
| 9 | MFA challenge flow incomplete | High | **Open** |
| 10 | Admin endpoints returned `str(exc)` | High | **Fixed centrally** — covers all 344 sites, not just admin_api |
| 11 | Repo hygiene: no `LICENSE`, `.pytest_cache` tracked | Medium | **Fixed** — MIT `LICENSE` added; artifacts untracked, files preserved |
| 12 | Many audit/status documents disagreeing | Medium | **Fixed here** — this is now the single source of truth |

---

## Go engine — measured, built, and now doing the work

The audit document claimed the repository had "one .go file and a Go module only
under sdk/go/, rather than a root-level Go module". Both halves were wrong.
`go.mod` sits at the repository root, and the measured inventory is in
[GO_BASELINE.md](GO_BASELINE.md):

```
go build ./...   clean
go vet ./...     clean
80 packages passing, 0 failing
gofmt clean for the main tree
1794 func Test functions across 134 files
```

Work completed on the Go side this cycle, all verified:

| Area | What |
|---|---|
| `internal/retrieval` | BM25 keyword search + reciprocal-rank-fusion hybrid search, owner-scoped |
| `tests/isolation` | adversarial cross-tenant suite: 12 cases, CI-required |
| `internal/evals` | recall@k / MRR / nDCG over a labelled corpus + a regression gate, CI-required |
| `internal/grounding` | citation accuracy: supported / uncited / missing / not-permitted |
| `internal/chat` | capability registry, model router, fallback chains, circuit breakers |
| `internal/chat` | resumable streaming: sequence numbers, cancel, replay on reconnect |
| `internal/sandbox` | adversarial escape suite; fixed a memory-budget leak it found |

Measured retrieval numbers, 10 documents, cutoff 5:

```
vector  recall 0.900  mrr 0.690  ndcg 0.736  misses 1 [cdc]
keyword recall 0.900  mrr 0.800  ndcg 0.821  misses 1 [rotation]
hybrid  recall 1.000  mrr 0.820  ndcg 0.859  misses 0
```

The hybrid recovers the miss each path had on its own, which is the entire
reason to fuse.

---

## Privileged endpoint audit — the largest open risk

`python scripts/audit_privileged_endpoints.py --json docs/PRIVILEGED_ENDPOINT_AUDIT.json`

| Metric | Count |
|---|---|
| Routes inspected | 1140 |
| Mutating routes | 624 |
| Routes with a caller-scoped parameter | 67 |
| Routes with an auth dependency | 500 |
| **Routes with no auth dependency** | **628** |
| — mutating | 329 |
| — scoped parameter | 33 |

The highest-count prefixes are `api` (78), `temporal` (60), `aios` (48), `omniscient` (43),
`observability` (36).

This needs stating plainly: several **unauthenticated `DELETE` endpoints exist**, including
`/compliance/organizations/{org_id}/gdpr/delete` and certification management under
`/security/organizations/{org_id}/...`. This is exploitable today by anyone who can reach the
service, and it is the single highest-priority item on this page.

Remediation is mechanical (attach the existing dependency) but large, and it needs care: some routes
are genuinely public (health probes, login), and some are mounted sub-applications whose auth is
enforced by a parent. The audit script distinguishes "expected public" from "needs auth" and exits
non-zero only on the latter, so it can be wired into CI as a ratchet.

---

## Test-suite defects fixed

These are recorded because each one silently invalidated prior claims:

- **Three concatenated modules** `database/database.py` and `app/auth_utils.py` — duplicated
  definitions where only the last was reachable, plus unreachable code
- **Conflicting env var spellings** between the two database modules — schema in one file, queries
  in another
- **Unreachable fallback** after a `raise` in both supabase client modules
- **12 `get_db().__enter__()` leaks** across 6 modules
- **Five `time.sleep` inside `async def`** blocking the event loop for all users
- **Two deadlocks**: `ResourcePool.acquire()` on its own non-reentrant lock, and
  `cleanup_expired` holding the lock while calling `_archive`
- **A self-recursive test** that ran the whole suite from inside the suite
- **Synchronous SQL strings** rejected by SQLAlchemy 2.x (raw `?` placeholders / positional rows)
- **A non-existent `CircuitBreaker.call()`** that failed every sandboxed tool
- **Backup filename collisions** that silently discarded backups taken in the same second

---

## Deliberately not claimed

These are **UNVERIFIED**, listed so that no one infers them from a green suite:

- RLS / cross-tenant isolation on a real PostgreSQL database — needs a real Postgres and separate
  roles; **not run**
- Browser E2E for the five flows — Playwright is not installed in this environment; **not run**
- Public benchmarks (MMLU-Pro, GPQA, HumanEval, …) — no API keys; **not run**
- The Go inference engine benchmarked against vLLM/llama.cpp — no GPU or model access; **not run**
- The 393 remaining failures **have not been triaged individually**; their causes are diagnosed at
  the class level only
- The 628 endpoint-audit findings **have not been remediated**
- No commit has been made; all changes are in the working tree

## What is claimed

- The security and integration suites are green and terminate reliably
- All five Critical security findings are fixed with regression tests that fail before the fix
- The suite is now honest: it is collected, it runs, and it reports

---

## Recommended next steps, in order

1. Remediate the 628 endpoint-audit findings, starting with the 329 mutating routes. Highest risk
   on the page.
2. Triage and fix the `tests/performance` failures (18) — they are stale patches against a changed
   API and hard-coded latency baselines, not infrastructure.
3. MFA challenge/verification completeness.
4. Wire the endpoint audit and coverage gate into required CI checks so they cannot regress.
5. Commit the working tree in small, one-concern commits before starting new work.
