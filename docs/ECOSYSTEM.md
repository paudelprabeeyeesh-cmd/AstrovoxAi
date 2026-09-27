# AI Ecosystem

Plugin registry, SDKs, extension marketplace, and developer tools.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      AI ECOSYSTEM                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │   Plugin     │    │   SDK        │    │   Extension          │  │
│  │   Registry   │    │   Generator  │    │   Marketplace        │  │
│  └──────┬───────┘    └──────────────┘    └──────────┬───────────┘  │
│         │                                            │               │
│  ┌──────▼────────────────────────────────────────────▼───────────┐  │
│  │                    Developer Portal                             │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │  │
│  │  │  API Keys    │  │  Webhooks    │  │  Analytics           │  │  │
│  │  │  Management  │  │  Management  │  │  Dashboard           │  │  │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │   Package    │    │   Plugin     │    │   Verification       │  │
│  │   Registry   │    │   Verifier   │    │   Pipeline           │  │
│  └──────────────┘    └──────────────┘    └──────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Plugin Registry

Central registry for plugins, extensions, and integrations.

### Backend Implementation

```python
from astrovox_ai.backend.app.ecosystem.plugin_registry import (
    PluginRegistry,
    PluginManifest,
    PluginPermission
)

registry = PluginRegistry()

# Register plugin
manifest = PluginManifest(
    name="my-plugin",
    version="1.0.0",
    description="My awesome plugin",
    permissions=[
        PluginPermission.CHAT_READ,
        PluginPermission.CHAT_WRITE,
        PluginPermission.FILES_READ
    ],
    entry_point="src/index.ts"
)

registry.register(manifest)
```

### Plugin Lifecycle

| State | Description |
|-------|-------------|
| `draft` | Plugin is being developed |
| `pending_review` | Submitted for verification |
| `verified` | Passed verification pipeline |
| `published` | Listed in marketplace |
| `deprecated` | No longer maintained |
| `archived` | Hidden from marketplace |

## SDK Generator

Auto-generate SDKs from OpenAPI specification.

```python
from astrovox_ai.sdk.generator import SDKGenerator

generator = SDKGenerator(
    spec_path="sdk/openapi/openapi.yaml",
    output_dir="sdk/generated"
)

# Generate all SDKs
generator.generate_all()

# Generate specific SDK
generator.generate_python(output_dir="sdk/python")
generator.generate_typescript(output_dir="sdk/typescript")
generator.generate_go(output_dir="sdk/go")
generator.generate_rust(output_dir="sdk/rust")
```

## Extension SDK

Build extensions for AstrovoxAI platforms.

```typescript
import { AstrovoxExtension, Message, Context } from '@astrovox/extension-sdk'

const extension = new AstrovoxExtension({
  name: 'my-extension',
  version: '1.0.0',
  apiKey: process.env.ASTROVOX_API_KEY
})

extension.onMessage(async (message: Message, context: Context) => {
  // Custom processing
  return message
})

extension.onCommand('custom-command', async (args) => {
  // Custom command logic
  return { result: 'success' }
})

export default extension
```

## Package Registry

Public registry for plugins and templates.

```bash
# Publish package
astrovox publish ./my-plugin

# Install package
astrovox install @community/my-plugin

# Search packages
astrovox search plugin "summarize"
```

## Plugin Verification

Security and quality verification pipeline.

```bash
# Verify plugin locally
astrovox verify ./plugin.tar.gz

# Check verification status
astrovox verify status @community/my-plugin@1.0.0
```

## Roadmap Portal

Public roadmap with community voting.

```bash
# List roadmap items
astrovox roadmap list --status planned

# Vote on feature
astrovox roadmap vote <item_id> --direction up

# Subscribe to updates
astrovox roadmap subscribe <item_id>
```

## Developer Portal

Unified control plane for ecosystem participants.

```bash
# Open portal
astrovox portal open

# Manage API keys
astrovox keys create --name "production" --scopes "chat,agents"

# Manage webhooks
astrovox webhooks create --url https://example.com/hook --events "message.created"
```

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/ecosystem/plugins` | List installed plugins |
| POST | `/ecosystem/plugins/install` | Install a plugin |
| DELETE | `/ecosystem/plugins/{id}` | Uninstall a plugin |
| POST | `/ecosystem/plugins/{id}/enable` | Enable a plugin |
| POST | `/ecosystem/plugins/{id}/disable` | Disable a plugin |
| POST | `/ecosystem/plugins/{id}/invoke` | Invoke plugin method |
| GET | `/ecosystem/marketplace/listings` | Search marketplace |
| POST | `/ecosystem/marketplace/listings/{id}/install` | Install from marketplace |
| POST | `/ecosystem/api/keys` | Issue API key |
| GET | `/ecosystem/api/keys` | List API keys |
| DELETE | `/ecosystem/api/keys/{id}` | Revoke API key |
| POST | `/ecosystem/webhooks/subscriptions` | Create webhook subscription |
| GET | `/ecosystem/webhooks/deliveries` | List webhook deliveries |
| GET | `/ecosystem/public/roadmap` | Public roadmap |

## Extension Points

- **Plugins**: Extend platform functionality
- **Custom Providers**: Add new AI model providers
- **Webhooks**: React to platform events
- **Integrations**: Connect third-party services
- **Templates**: Share agent and workflow templates
- **Themes**: Custom UI themes

## Monetization (Future)

- Plugin marketplace revenue sharing (15% platform fee)
- Premium support tiers
- Enterprise licensing
- Managed model hosting fees
