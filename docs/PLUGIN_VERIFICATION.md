# Plugin Verification

Plugin verification ensures that every published plugin meets security, compatibility, and quality standards before it reaches the marketplace.

## Verification Pipeline

```
Source → Sign → Scan → Sandbox → Approve → Publish
```

### 1. Sign

The maintainer signs the plugin package with a GPG or Sigstore key. The registry stores the signature alongside the tarball.

### 2. Scan

Automated static analysis checks for:

- Hardcoded secrets or API keys
- Dangerous subprocess execution
- Network access to unauthorized hosts
- Excessive permission scope requests
- License compliance (no GPL contamination in proprietary plugins)

### 3. Sandbox

The plugin runs in a gVisor or Firecracker microVM with:

- Network egress restricted to declared allowlist
- Filesystem access scoped to plugin data directory
- CPU and memory limits enforced
- No host PID or namespace access

### 4. Test Suite

Maintainers provide a CI test suite. The verification runner executes:

- Unit tests
- Integration tests against a mock AstrovoxAI instance
- Permission boundary tests (plugin must fail when accessing undeclared resources)

### 5. Approve

AstrovoxAI maintainers review flagged results. A clean run yields a signed verification attestation.

## Attestation

```json
{
  "plugin": "@community/summarizer",
  "version": "1.2.0",
  "verified_at": "2026-09-26T08:00:00Z",
  "scans": {
    "static": "pass",
    "sandbox": "pass",
    "tests": "pass"
  },
  "signature": "-----BEGIN SIGSTORE ..."
}
```

## CLI

```bash
astrovox verify ./plugin.tar.gz
astrovox verify @community/summarizer@1.2.0
astrovox verify status @community/summarizer
```

## Policy

- Unverified plugins can still be installed with `--allow-unverified`
- Enterprise tenants may require 100% verified plugins
- Verification attestations expire after 90 days and must be renewed
