# AI Ecosystem

AstrovoxAI Phase 19 — a connected ecosystem of SDKs, packages, extensions, templates, docs, and integrations.

## Capabilities

- **Official SDKs** — Python, TypeScript, Go, Rust, Java, C# (`sdk/`)
- **Package Registry** — publish, version, and consume Astrovox packages (`sdk/package-registry/`)
- **Extension Marketplace** — discover and install IDE and browser extensions (`extensions/marketplace/`)
- **Plugin Verification** — sandboxed validation, signed manifests, provenance checks (`extensions/verification/`)
- **Template Library** — starter kits for agents, plugins, and integrations (`sdk/template-library/`)
- **Developer Portal** — unified dashboard for API keys, webhooks, and deployments (`frontend/developer.html`)
- **API Playground** — interactive request builder with live responses (`docs/API_PLAYGROUND.md`)
- **Interactive Docs** — browser-based reference with runnable examples (`docs/INTERACTIVE_DOCS.md`)
- **CLI Improvements** — scaffold, publish, verify, and deploy from the terminal (`cli/commands/`)
- **IDE Integrations** — VS Code, JetBrains, Neovim, Chrome, Firefox, Safari (`extensions/`)
- **Webhook Ecosystem** — HMAC-SHA256 signatures, retries, DLQ, per-event filters (`docs/WEBHOOK_ECOSYSTEM.md`)
- **Third-Party Integrations** — GitHub, GitLab, Slack, Discord, Google Drive, OneDrive, Dropbox, Notion, Jira, Trello (`docs/INTEGRATIONS.md`)
- **Community Benchmarks** — latency, throughput, cost, and quality leaderboards (`sdk/benchmark/`)
- **OpenAPI Spec** — machine-readable API contract (`sdk/openapi/openapi.yaml`)
- **Roadmap Portal** — public voting, status tracking, and release notes (`docs/ROADMAP_PORTAL.md`)

## Directory Map

| Area | Path |
|------|------|
| SDKs | `sdk/{python,typescript,go,rust,java,csharp,openapi}/` |
| Package Registry | `sdk/package-registry/` |
| Template Library | `sdk/template-library/` |
| Benchmarks | `sdk/benchmark/` |
| Extensions | `extensions/{vscode,jetbrains,neovim,chrome,firefox,safari,shared}/` |
| Marketplace | `extensions/marketplace/` |
| Plugin Verification | `extensions/verification/` |
| Docs | `docs/ECOSYSTEM.md`, `docs/DEVELOPER_PORTAL.md`, ... |
| Frontend | `frontend/developer.html` |

## Quick Start

```bash
# Install SDK
pip install astrovox
npm install @astrovox/sdk

# Publish a package
astrovox publish ./my-plugin

# Verify a plugin
astrovox verify ./plugin.tar.gz

# Browse marketplace
astrovox marketplace search agent
```
