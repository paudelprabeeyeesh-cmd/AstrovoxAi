# AstrovoxAI Python SDK

Official Python SDK for AstrovoxAI.

## Installation

```bash
pip install astrovox
```

## Quick Start

```python
from astrovox import AstrovoxClient

client = AstrovoxClient(api_key="avx_...")
conversation = client.create_conversation(title="My Chat")
response = client.send_message(conversation.id, "Hello, Astrovox!")
print(response)
```

See [sdk/python/](../sdk/python/) for the full source code and [Python SDK Guide](/sdk/python) for documentation.
