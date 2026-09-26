# OpenAPI Specification

The AstrovoxAI OpenAPI specification is the machine-readable contract for the entire public API.

## Files

| File | Description |
|------|-------------|
| `sdk/openapi/openapi.yaml` | OpenAPI 3.1 spec |
| `sdk/openapi/spec.py` | Python spec loader and validator |
| `sdk/openapi/__init__.py` | Package init |

## Endpoint Groups

- `/v1/chat/*` — Chat completions and streaming
- `/v1/agents/*` — Agent runtime and tool execution
- `/v1/models/*` — Model catalog and metadata
- `/v1/embeddings/*` — Text embedding generation
- `/v1/search/*` — Semantic and hybrid search
- `/v1/vision/*` — Image analysis and OCR
- `/v1/audio/*` — Transcription and synthesis
- `/ecosystem/plugins/*` — Plugin lifecycle
- `/ecosystem/webhooks/*` — Webhook management
- `/ecosystem/integrations/*` — Third-party connectors
- `/ecosystem/api/keys/*` — API key issuance and rotation

## Generate SDKs

```bash
# Python
openapi-generator generate -i sdk/openapi/openapi.yaml -g python -o sdk/python_generated

# TypeScript
openapi-generator generate -i sdk/openapi/openapi.yaml -g typescript-axios -o sdk/typescript_generated

# Go
openapi-generator generate -i sdk/openapi/openapi.yaml -g go -o sdk/go_generated

# Rust
openapi-generator generate -i sdk/openapi/openapi.yaml -g rust -o sdk/rust_generated
```

## Validate Spec

```bash
python -m sdk.openapi.spec validate
swagger-cli validate sdk/openapi/openapi.yaml
```

## Serve Locally

```bash
npx @redocly/cli serve-docs sdk/openapi/openapi.yaml
# Opens at http://localhost:8080
```

## Versioning

The spec is versioned under `sdk/openapi/`. Breaking changes require a new minor version bump and a migration guide in `docs/`.
