# Security Best Practices (Stage 22)

The Stage 22 ecosystem introduces powerful extensibility surfaces. The
following practices keep the platform safe.

## Plugin Isolation

- Plugins run with a curated sandbox surface (`PluginSandbox`).
- Network calls are routed through the host's HTTP client for visibility.
- Filesystem and environment access is brokered via `PluginStorage`.
- Use the dependency scanner (`POST /ecosystem/security/scan`) before
  installing a plugin from an unknown source.

## Permission Validation

- Permissions are explicitly declared in `plugin.json`.
- The host validates that requested permissions are within the allow-list.
- Call `PluginContext.require(permission)` to gate sensitive operations.
- Audit entries record every grant/revoke (`GET /ecosystem/audit`).

## Secret Management

- API keys, OAuth tokens, and integration tokens are encrypted at rest via
  `SecretVault` (AES-GCM).
- Use `POST /ecosystem/security/secrets/encrypt` and `/decrypt` from internal
  services; never expose these endpoints publicly.
- Avoid logging secrets; `SecretScrubber` redacts common patterns.

## API Authentication

- API keys are issued with both an `api_key` and `api_secret`. Verify both.
- OAuth tokens use bearer auth and are short-lived; refresh tokens are 30
  days.
- Rotate keys regularly; revoke old keys via `DELETE /ecosystem/api/keys/{id}`.

## Webhook Verification

- All outgoing webhooks include `X-Astrovox-Signature` (HMAC-SHA256).
- Reject deliveries with stale timestamps (older than 5 minutes).
- Persist the secret securely; never expose it via logs.

## Audit Logging

- All privileged actions (plugin install, key issue, integration connect,
  webhook subscription) are appended to `AuditLog` (`./storage/ecosystem/audit.jsonl`).
- Retrieve recent entries via `GET /ecosystem/audit`.

## Dependency Scanning

- `DependencyScanner` flags risky packages and unsafe Python patterns
  (`eval`, `exec`, `os.system`).
- Run scans in CI before publishing plugins to the marketplace.

## Supply-Chain

- Plugin manifests carry SHA-256 checksums; the host verifies before
  extraction.
- Marketplace listings surface version history so users can audit changes.