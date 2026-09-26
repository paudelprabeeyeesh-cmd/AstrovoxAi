# API Playground

The API Playground provides an interactive environment for exploring AstrovoxAI endpoints without writing code.

## Access

1. Open `frontend/developer.html`
2. Select the **Playground** tab
3. Choose an endpoint and enter a request body
4. Click **Send Request**

## Supported Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/chat/completions` | POST | Chat completion |
| `/v1/chat/stream` | POST | Streaming chat |
| `/v1/agents` | POST | Agent execution |
| `/v1/models` | GET | List models |
| `/v1/embeddings` | POST | Generate embeddings |
| `/v1/search/semantic` | POST | Semantic search |
| `/v1/vision/analyze` | POST | Image analysis |
| `/v1/audio/transcribe` | POST | Audio transcription |

## Authentication

The playground automatically injects the active API key from the portal session. To use a custom key, set it in the **API Keys** tab first.

## Request Builder

- Select endpoint from dropdown
- Edit JSON body in the textarea
- Choose HTTP method
- Add custom headers
- View response with syntax highlighting
- Copy cURL command for the request

## Example

```json
POST /v1/chat/completions
{
  "model": "gpt-4",
  "messages": [
    {"role": "user", "content": "Explain quantum computing"}
  ],
  "temperature": 0.7,
  "max_tokens": 256
}
```

Response:

```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "Quantum computing is..."
      }
    }
  ]
}
```

## CLI Equivalent

```bash
astrovox playground --endpoint /v1/chat/completions --body '{"model":"gpt-4","messages":[{"role":"user","content":"Hello"}]}'
```
