# Capability Assessment

`go run ./cmd/capability/` runs twelve suites and prints a report. It
deliberately does not print a single number.

There is no accepted AGI benchmark. A repository that prints "AGI Score:
98%" with no methodology is making the exact overclaiming the engineering
register warns about, and a weighted average over suites that cover
different surfaces hides which ones ran. So the output is a table of what
ran, what passed, and what each suite covers.

## Latest run

```
capability assessment: 12/12 suites green
cases: 243 passed, 0 failed, 0 skipped
```

| Suite | Cases | What it measures |
|---|---|---|
| security.ssrf | 13 | the guard resolves the hostname before it allows the connection, so a private address is refused by construction and not by a filter applied after the request |
| security.tokens | 14 | tokens are 256-bit, single-use, purpose-scoped, and expiring; a reset token cannot be redeemed as a magic link |
| security.idempotency | 12 | a retried write does not execute twice, and ten concurrent requests with one key execute the handler once |
| security.logging | 14 | a credential held in a field under any name — including a differently-cased header key — is redacted |
| server.identity | 31 | register, login, verify, reset, and magic-link flows, and the resistance of every one of them to account enumeration |
| server.http | 19 | the error envelope, the auth chain, and tenant scoping on every route |
| server.chat | 17 | the spend gate runs before the provider call, so a request that would breach the budget never spends |
| retrieval.acl | 25 | the owner is inside the search key, so a cross-tenant search is impossible rather than filtered |
| memory.policy | 17 | the memory store refuses sensitive and instruction-shaped candidates |
| tools.budget | 52 | arguments are validated before execution, and repeated or runaway loops are capped |
| conversations.scoping | 15 | cross-tenant read, write, and delete all fail |
| capability.report | 14 | the assessment itself reports honestly |

## What this does not measure

The honest limits of the number above:

- **No model was called.** The suites score implementation properties
  (does the guard refuse, is the token single-use, is the write scoped),
  not answer quality. Nothing here says the product gives good answers.
- **No answer-quality evaluation is wired in yet.** The eval set in
  `evals/` exists and is tested, but it is not run by this command.
- **No provider was reached.** No OpenAI, Anthropic, or Stripe call is
  exercised by these suites.
- **No HTTP server was booted.** The suites drive the router through
  httptest.
- **No durable store.** Every store is in-process, so a restart loses it.
- **No multimodal, training, or distributed-inference measurement.** Those
  subsystems exist as code and are not covered here.

A reader who wants to know whether this system is "98% of the way to
AGI" will not get an answer from this document, and no document built on
these suites could give one. What it does give is: 243 measured
properties, all passing, across the twelve surfaces that decide whether an
AI product is safe to run.

## Reproducing

```bash
go run ./cmd/capability/           # human-readable
go run ./cmd/capability/ -json     # machine-readable, exits non-zero on failure
```

Each suite is a normal `go test ./...` invocation; the command adds no
logic of its own beyond counting pass and fail actions.
