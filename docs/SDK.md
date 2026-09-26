# SDK / CLI / API / GraphQL

AstrovoxAI provides comprehensive SDKs and APIs for integrating AI capabilities into any application.

## REST API
Base URL: `https://api.astrovox.ai/v1`

### Endpoints
- `POST /v1/chat/completions` — Chat completion
- `POST /v1/chat/stream` — Streaming chat
- `POST /v1/completions` — Text completion
- `GET /v1/models` — List models
- `POST /v1/embeddings` — Generate embeddings
- `POST /v1/chat/agent` — Agent execution
- `POST /v1/vision/analyze` — Image analysis
- `POST /v1/audio/transcribe` — Audio transcription
- `POST /v1/search/semantic` — Semantic search

## GraphQL
Endpoint: `https://api.astrovox.ai/v1/graphql`

```graphql
query Chat($conversationId: ID!, $message: String!) {
  chat(conversationId: $conversationId, message: $message) {
    id
    role
    content
    timestamp
  }
}
```

## gRPC
Proto files available in `sdk/openapi/`.

## SDKs
- **Python**: `pip install astrovox-ai`
- **TypeScript**: `npm install @astrovox-ai/sdk`
- **Go**: `go get github.com/astrovox/astrovox-ai/go`
- **Java**: Maven Central
- **Rust**: `cargo add astrovox-ai`
- **C#**: NuGet `AstrovoxSDK`

## CLI
```bash
# Install
npm install -g @astrovox-ai/cli

# Usage
astrovox chat "Explain quantum computing"
astrovox models list
astrovox embeddings create --text "Hello world"
```
