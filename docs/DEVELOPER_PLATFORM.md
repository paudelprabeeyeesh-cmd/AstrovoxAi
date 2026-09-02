# AstrovoxAI Developer Platform (Stage 22)

Stage 22 transforms AstrovoxAI from a single-tenant AI backend into a
connected ecosystem. Users can install plugins, use official SDKs, integrate
external services, and subscribe to webhook events.

## Capabilities

- **Plugin Framework** — version-aware installer, lifecycle hooks, sandbox,
  permission model, dependency resolution, update/uninstall flows.
- **Public API Platform** — REST surface, API key issuance, OAuth 2.0
  (authorization code + client credentials + refresh), rate limiting, and
  analytics aggregation.
- **Webhooks** — incoming and outgoing webhooks, HMAC-SHA256 signature
  verification, retries with exponential backoff, DLQ, and per-event
  filters.
- **Third-Party Integrations** — connectors for GitHub, GitLab, Slack,
  Discord, Google Drive, OneDrive, Dropbox, Notion, Jira, and Trello with
  OAuth + secret storage.
- **Marketplace** — catalog, search, ratings, categories, install/uninstall
  manager, version history, permission overview, and update notifications.
- **Official SDKs** — Python (`app.ecosystem.sdk`) and JavaScript/TypeScript
  (`examples/astrovox-sdk`).
- **Monitoring & Security** — ecosystem event monitor, audit log, secret
  vault (AES-GCM), and dependency scanner.

## Endpoint Map

| Group | Prefix | Examples |
|-------|--------|----------|
| Plugins | `/ecosystem/plugins` | list, install, enable, disable, invoke |
| API Keys | `/ecosystem/api/keys` | issue, list, OAuth token exchange |
| Webhooks | `/ecosystem/webhooks` | subscribe, publish, deliveries, DLQ |
| Integrations | `/ecosystem/integrations` | catalog, connect, invoke |
| Marketplace | `/ecosystem/marketplace` | search, install, rate |
| Monitoring | `/ecosystem/monitoring` | summary, health, adoption |
| Audit | `/ecosystem/audit` | tail, filter |
| Public | `/ecosystem/public` | unauthenticated info & health |

See `ECOSYSTEM.md` for the full reference.