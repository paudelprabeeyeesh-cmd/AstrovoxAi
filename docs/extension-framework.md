# Extension Framework

AstrovoxAI provides an extension framework for building IDE plugins, browser extensions, and custom integrations.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     EXTENSION FRAMEWORK                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │  Extension   │    │  Shared      │    │  Registry        │  │
│  │  SDK         │◄──►│  Core        │    │  & Discovery     │  │
│  └──────────────┘    └──────────────┘    └──────────────────┘  │
│         │                    │                    │             │
│  ┌──────▼───────────────────────────────────────────────────┐  │
│  │                    Host Integration Layer                  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Supported Platforms

| Platform | Location | Status |
|----------|----------|--------|
| VS Code | `extensions/vscode/` | Stable |
| JetBrains | `extensions/jetbrains/` | Stable |
| Chrome | `extensions/chrome/` | Stable |
| Firefox | `extensions/firefox/` | Stable |
| Safari | `extensions/safari/` | Stable |
| Neovim | `extensions/neovim/` | Beta |

## Extension SDK

```python
from extensions.framework.extension_sdk import Extension, Tool

class MyExtension(Extension):
    name = "my-extension"
    version = "1.0.0"

    def register_tools(self):
        return [
            Tool(name="greet", description="Say hello", func=self.greet)
        ]

    def greet(self, name: str) -> str:
        return f"Hello, {name}!"
```

## Extension Manifest

```json
{
  "name": "my-extension",
  "version": "1.0.0",
  "api_version": "1",
  "permissions": ["chat.read", "chat.write"],
  "entry_point": "main.py"
}
```

## Publishing

Extensions are published to the AstrovoxAI Marketplace. See `marketplace/plugin_registry.py` for registration logic.

## Security

- All extensions are sandboxed.
- Permissions are declared in the manifest and enforced at runtime.
- Extensions must pass verification before appearing in the marketplace.
