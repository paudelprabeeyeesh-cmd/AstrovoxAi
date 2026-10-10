# Leadership & Process

## Architecture Reviews

- ADRs live in `docs/adr/` (currently 20 records covering module layout, dtype
  promotion, error semantics, backend abstraction, and checkpoint design).
- Every cross-layer interface change requires an ADR; `docs/architecture-review.md`
  records the standing review checklist.
- Layering is enforced mechanically: `go vet ./...` plus the arch layering check
  in `internal/arch` runs in CI.

## Code Reviews

`docs/coding_standards.md` + `docs/CONTRIBUTING.md` define the review rules. The
CI gate (`.github/workflows/ci.yml`) enforces the mechanical half:

| Gate | Command |
|---|---|
| Build | `go build ./...` |
| Vet | `go vet ./...` |
| Race tests | `go test -race ./...` |
| Formatting | `gofmt -l .` |
| Module tidiness | `go mod tidy` diff check |
| Test-count floor | `go test ./... -v \| grep -c '^=== RUN'` ≥ 1000 |

Human reviewers focus on what CI cannot check: naming, error semantics, ADR
compliance, and whether a new subsystem belongs at its chosen layer.

## Release Planning

`docs/release_strategy.md` and `docs/roadmap.md` govern versioning. Semver
majors track IR/API changes; minors add subsystems; patches are bug fixes only.

## Milestone Reviews

The master checklist (`docs/ASTROVOX_MASTER_CHECKLIST.md`) is the milestone
source of truth: a phase is closed when its modules are marked and the CI gates
pass. Current status: 229 modules, all but the hardware/platform-dependent ones
delivered (see `docs/IMPOSSIBLE_MODE_DELIVERY.md`).

## Technical Decision Records

Conventions for ADRs (context / decision / consequences / status) are in
`docs/adr/`. Numbers are never reused; a superseded ADR is marked *superseded*
rather than rewritten, so history stays auditable.

## Mentoring & Team Standards

`docs/ONBOARDING.md` is the ramp path; `docs/runbooks/` holds the operational
playbooks. New subsystems land with tests first, then docs, then an ADR entry.