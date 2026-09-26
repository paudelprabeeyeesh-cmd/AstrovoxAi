# Package Registry

The Astrovox Package Registry is a public registry for plugins, templates, SDK extensions, and integrations.

## Registry URL

```
https://packages.astrovox.ai
```

## Publish a Package

```bash
# Login
astrovox login

# Publish
astrovox publish ./my-astrovox-plugin

# Publish a template
astrovox publish ./my-agent-template --type template
```

## Package Structure

A minimal package:

```
my-plugin/
  astrovox.json
  README.md
  src/
    index.ts
  tests/
    index.test.ts
```

`astrovox.json`:

```json
{
  "name": "@scope/my-plugin",
  "version": "1.0.0",
  "description": "My awesome plugin",
  "author": "you@example.com",
  "license": "MIT",
  "astrox": {
    "type": "plugin",
    "entry": "src/index.ts",
    "permissions": ["storage:read", "webhooks:subscribe"]
  },
  "scripts": {
    "test": "astrovox test"
  }
}
```

## Registry API

```bash
# Search
GET /v1/registry/packages?q=agent

# Package info
GET /v1/registry/packages/@scope/my-plugin

# Download
GET /v1/registry/packages/@scope/my-plugin/-/my-plugin-1.0.0.tgz

# Verify integrity
GET /v1/registry/packages/@scope/my-plugin/integrity
```

## Versioning

- Semver is enforced: `MAJOR.MINOR.PATCH`
- Deprecated versions are retained for 90 days
- Registry checks signatures before publishing

## Scopes

| Scope | Description |
|-------|-------------|
| `@astrovox/official` | Maintained by AstrovoxAI |
| `@community` | Community-contributed |
| `@verified` | Verified publishers |
| `@experimental` | Experimental packages |

## Integration with CLI

```bash
astrovox search plugin "summarize"
astrovox install @community/summarizer
astrovox info @astrovox/official/pdf-loader
```
