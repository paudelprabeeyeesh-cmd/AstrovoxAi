# Threat Model — Code Execution Sandbox

The sandbox runs model-generated code. That is one of the highest-risk
features in the system, because the code is written by an attacker who
controls its contents, and it runs on hardware that holds other users' data.
This document states what the sandbox must withstand. Code implementing it
does not exist yet; this is the model the implementation is judged against.

## 1. Assets

| Asset | Why it matters |
|---|---|
| Host kernel, other containers | A sandbox escape escalates to every tenant |
| Other tenants' data | Cross-tenant read is a reportable breach |
| Network position | An in-cluster foothold reaches Postgres, Redis, metadata APIs |
| Provider credentials | A leaked key bills the account or exfiltrates data |
| Availability | Compute exhaustion denies service to everyone |

## 2. Attackers and goals

| Attacker | Goal | Entry |
|---|---|---|
| Product user | Read other tenants, reach the metadata service | generated code |
| Remote attacker | Inbound from an exposed port | network egress policy |
| Supply chain | Code execution at start | prebuilt image, pinned deps |
| Compromised admin | Move laterally | out of scope for the sandbox, covered by D17-12 |

## 3. Attack surface

1. Source of the program itself (arbitrary text).
2. Language runtime and standard library (`import`, `open`, `subprocess`).
3. Installed packages (install-at-runtime = arbitrary code execution).
4. Filesystem: workspace mount, temp directory, sockets.
5. Network: DNS, TCP, UDP.
6. Resource usage: memory, CPU, processes, disk, wall time, output size.

## 4. Required controls

| Control | Requirement | Test |
|---|---|---|
| No network by default | Egress denied unless explicitly granted | requests to disallowed hosts fail |
| No installs at runtime | `pip`/`apt` unavailable in the image | install attempt fails |
| Read-only root | Only a temp workspace is writable | writing outside it fails |
| Dropped capabilities | No `SYS_ADMIN`, no raw sockets | escape probe fails |
| Fresh container per run | No state survives to the next run | files from one run invisible in the next |
| Resource limits | CPU, memory, processes, disk, wall time, stdout | infinite loop and huge-output terminate |
| Size limits | Input program, output, transfer | oversize rejected before execution |
| Timeout | Wall clock cap with kill on breach | run terminates at cap |

## 5. Escape scenarios considered

| Scenario | Expected behaviour |
|---|---|
| `os.system("curl http://metadata")` | DNS/egress blocked, command rejected |
| Fork bomb | Process limit kills the tree |
| Infinite loop | Wall-clock timeout kills the container |
| Root filesystem write | Read-only root fails the write |
| Mount escape path (`/proc/1/root`) | Namespace isolation blocks traversal |
| Side channel via timing | Documented as residual risk; not mitigated at this layer |
| Signal to host PID namespace | Isolated PID namespace |

## 6. Residual risks

Documented, not eliminated, at this layer:

- Side channels across tenants sharing a host are not mitigated by sandbox
  configuration alone; stronger isolation options (gVisor, Firecracker,
  managed sandboxes) are evaluated in D12-03.
- A compromised image build is a separate supply-chain concern (D17-06,
  D17-07).
- Runtime dependency confusion is mitigated by pinning and by refusing
  installs, not by dependency verification.

## 7. Review requirement

This document needs a second engineer's review before implementation is
considered complete, and the review needs to be recorded. Until that happens,
the sandbox is not authorized to run untrusted code in production.

## 8. Out of scope

Privileged access of operators, physical security of the hosting provider,
and compromise of the build pipeline are covered by other tasks
(D17-12, D17-06).