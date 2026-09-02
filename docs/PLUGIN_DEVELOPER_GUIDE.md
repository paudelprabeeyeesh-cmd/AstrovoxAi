# Plugin Developer Guide

This guide explains how to build, package, and ship plugins for the
AstrovoxAI platform.

## Manifest

Every plugin ships a `plugin.json` file describing its identity,
permissions, dependencies, and entry point:

```json
{
  "id": "github",
  "name": "GitHub",
  "version": "1.0.0",
  "author": "Your Org",
  "description": "Talk to GitHub repositories.",
  "category": "developer",
  "tags": ["git", "developer"],
  "permissions": ["network:outgoing", "files:read"],
  "entry_point": "github_plugin:Plugin",
  "min_platform_version": "2.0.0",
  "max_platform_version": "3.0.0"
}
```

### Permissions

Plugins must declare the permissions they require. The host enforces them at
runtime via the sandbox:

| Permission | Description |
|-----------|-------------|
| `memory:read` / `memory:write` | Long-term memory access |
| `files:read` / `files:write` | Managed file storage |
| `network:outgoing` / `network:incoming` | External HTTP traffic |
| `code:execute` | Run code in a sandbox |
| `users:read` | Read user profile data |
| `billing:read` | Read billing information |
| `agent:run` | Trigger agent runs |
| `webhook:publish` | Publish webhook events |
| `storage:read` / `storage:write` | Read/write storage objects |

## Plugin Class

```python
from app.ecosystem.plugins import _PluginBase

class Plugin(_PluginBase):
    manifest_id = "github"

    def on_enable(self):
        self.context.log_event("github.enabled")

    def list_repos(self, owner=None):
        self.context.require("network:outgoing")
        return {"owner": owner, "repos": []}
```

## Lifecycle Hooks

- `on_install()` – runs after the manifest is validated.
- `on_enable()` – runs when the user enables the plugin.
- `on_disable()` – runs when the user disables the plugin.
- `on_uninstall()` – last chance to clean up resources.
- `on_update(old, new)` – runs after an upgrade.

## Packaging

Create a `.zip` (or `.astrovox-plugin`) containing `plugin.json` and the
plugin source files. Users can install it with:

```
POST /ecosystem/plugins/install
{
  "source": "github",
  "permissions": ["network:outgoing"]
}
```

## SDK Helpers

The official SDK exposes helpers for install/enable/disable/invoke:

```python
from astrovoxai import AstrovoxClient

client = AstrovoxClient(base_url="https://api.astrovox.ai", api_key="...")
client.install_plugin("github", permissions=["network:outgoing"])
client.invoke_plugin("github", "list_repos", owner="astrovox-ai")
```