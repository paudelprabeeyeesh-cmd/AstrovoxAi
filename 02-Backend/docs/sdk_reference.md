# SDK Reference

## Installation

```bash
# Python
pip install astrovoxai

# JavaScript
npm install astrovoxai
```

## Quick Start

```python
import astrovoxai

client = astrovoxai.Client(api_key="astrovox-xxx")

response = client.solve(text="Hello world")
print(response.result)
```

```javascript
import { AstrovoxAI } from 'astrovoxai';

const client = new AstrovoxAI({ apiKey: 'astrovox-xxx' });

const response = await client.solve({ text: 'Hello world' });
console.log(response.result);
```

## Methods

### solve(text, options)
- `text`: string (required)
- `user_id`: string (required)
- `conversation_id`: string (optional)
- Returns: `SolveResponse`

### memory.create(key, value)
### memory.list()
### memory.search(query)
### memory.delete(id)

### conversations.create(title)
### conversations.list()
### conversations.search(query)
### conversations.get(id).messages

### templates.create(name, prompt, variables)
### templates.list()
### templates.update(id, data)
### templates.delete(id)

### knowledge.create(title, content)
### knowledge.list()
### knowledge.search(query)
### knowledge.delete(id)

### feedback.create(request_id, rating, comment)
### feedback.list()

## Rate Limits
- Free: 10 req/day
- Pro: 1,000 req/day
- Team: 10,000 req/day
- Enterprise: Custom

## Support
- Email: api@astrovox.ai
- Docs: https://docs.astrovox.ai
- Status: https://status.astrovox.ai
