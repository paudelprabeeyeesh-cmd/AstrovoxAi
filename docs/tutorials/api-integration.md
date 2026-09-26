# API Integration Tutorial

Learn how to integrate AstrovoxAI into your application using REST APIs directly.

## Authentication

All API requests require an API key in the `Authorization` header:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" https://api.astrovox.ai/v1/chat/completions
```

## Making a Request

```bash
curl -X POST https://api.astrovox.ai/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello!"}],
    "temperature": 0.7
  }'
```

## Streaming Responses

```bash
curl -X POST https://api.astrovox.ai/v1/chat/stream \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Tell me a story"}]
  }'
```

## Error Handling

| Status | Meaning |
|--------|---------|
| 400 | Bad request - check your JSON body |
| 401 | Unauthorized - check your API key |
| 429 | Rate limited - retry with backoff |
| 500 | Server error - contact support |

## Next Steps

- Explore the [API Playground](../docs/API_PLAYGROUND.md)
- Use the [CLI](../cli/README.md)
- Try an [SDK](../docs/SDK.md)
