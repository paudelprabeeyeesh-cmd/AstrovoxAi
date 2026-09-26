# Plugin Development Tutorial

This tutorial shows how to build and publish a plugin for AstrovoxAI.

## Plugin Structure

A plugin is a Python package with an entry point and a manifest:

```
my-plugin/
  manifest.json
  main.py
  README.md
```

## Manifest

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "My custom plugin",
  "author": "Your Name",
  "category": "tools",
  "permissions": ["chat.read", "chat.write"],
  "entry_point": "main.py"
}
```

## Implementation

```python
# main.py
from extensions.framework.extension_sdk import Extension, Tool

class MyPlugin(Extension):
    manifest = ExtensionManifest(
        name="my-plugin",
        version="1.0.0",
        category="tools",
        permissions=["chat.read", "chat.write"],
    )

    def register_tools(self):
        return [
            Tool(
                name="my_tool",
                description="Does something useful",
                func=self.do_something,
            )
        ]

    def do_something(self, input: str) -> str:
        return f"Processed: {input}"

extension = MyPlugin()
```

## Testing

```bash
astrovox plugin test ./my-plugin
```

## Publishing

```bash
astrovox plugin publish ./my-plugin
```

## Next Steps

- Read the [Extension Framework Docs](../docs/extension-framework.md)
- Browse the [Marketplace](../marketplace/plugin-directory.md)
