# SDK Documentation

AstrovoxAI ships official SDKs for Python and JavaScript/TypeScript. Both
follow the same naming conventions and authentication model.

## Installation

```bash
# Python
pip install astrovoxai

# JavaScript / TypeScript
npm install @astrovoxai/sdk
```

## Authentication

```python
# Python
from astrovoxai import AstrovoxClient
client = AstrovoxClient(
    base_url="https://api.astrovox.ai",
    api_key="ak_...",
    api_secret="sk_...",
)
```

```ts
// TypeScript
import { AstrovoxClient } from "@astrovoxai/sdk";

const client = new AstrovoxClient({
  baseUrl: "https://api.astrovox.ai",
  apiKey: process.env.ASTROVOX_KEY!,
  apiSecret: process.env.ASTROVOX_SECRET!,
});
```

## Common Operations

| Operation | Python | TypeScript |
|-----------|--------|------------|
| Send chat | `client.chat([...])` | `client.chat([...])` |
| List plugins | `client.list_plugins()` | `client.listPlugins()` |
| Install plugin | `client.install_plugin("github")` | `client.installPlugin("github")` |
| Invoke plugin | `client.invoke_plugin("github", "list_repos", owner="x")` | `client.invokePlugin("github", "list_repos", ["x"])` |
| Create API key | `client.create_api_key(...)` | `client.createApiKey(...)` |
| Subscribe webhook | `client.create_webhook(url, events)` | `client.createWebhook(url, events)` |
| Connect integration | `client.connect_integration("slack", "Main")` | `client.connectIntegration("slack", "Main")` |
| Search marketplace | `client.marketplace_search(q="chat")` | `client.marketplaceSearch({ q: "chat" })` |

## Error Handling

```python
from astrovoxai import AstrovoxError

try:
    client.invoke_plugin("github", "list_repos")
except AstrovoxError as exc:
    print(exc.status, exc.payload)
```

```ts
try {
  await client.invokePlugin("github", "list_repos");
} catch (err) {
  if (err instanceof AstrovoxError) {
    console.error(err.status, err.payload);
  }
}
```

## Webhook Signatures

Both SDKs ship a `signPayload`/`verifyPayload` helper that implements the
`X-Astrovox-Signature` scheme. Use it on your receiving endpoints.

## Versioning

The SDKs follow semver. The current major version is `1.x`; breaking changes
will be announced in the changelog at least one minor release ahead.